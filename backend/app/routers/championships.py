from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.db import get_session
from app.deps import get_optional_user, require_moder_plus, require_pilot_plus
from app.models import (
    Championship,
    ChampionshipRegistration,
    ChampionshipScoringSystem,
    RACE_GAMES,
    Race,
    RaceRegistration,
    RaceStatus,
    Role,
    Team,
    TeamApplicationStatus,
    User,
    UserStatus,
)
from app.rate_limit import limiter
from app.race_assets import RACE_ASSET_GAMES, assets_for_game, get_race_assets
from app.schemas import (
    ChampionshipApplyRequest,
    ChampionshipCarUpdate,
    ChampionshipCreate,
    ChampionshipParticipantAdd,
    ChampionshipRead,
    ChampionshipRegistrationModeration,
    ChampionshipStageAdd,
    ChampionshipStageUpdate,
    ChampionshipUpdate,
)
from app.services import result_rows


router = APIRouter()

FIA_POINTS = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}
ENDURANCE_POINTS = {1: 38, 2: 27, 3: 23, 4: 18, 5: 15, 6: 12, 7: 9, 8: 6, 9: 3, 10: 2}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def championship_status(championship: Championship, current_time: datetime | None = None) -> str:
    if not championship.is_published:
        return "draft"
    current = current_time or now_utc()
    registration_start = as_utc(championship.registration_start)
    registration_end = as_utc(championship.registration_end)
    championship_start = as_utc(championship.championship_start)
    championship_end = as_utc(championship.championship_end)
    if registration_start <= current <= registration_end:
        return "registration_open"
    if championship_start <= current <= championship_end:
        return "active"
    if current > championship_end:
        return "finished"
    return "upcoming"


def update_stage_time_status(stage: Race) -> bool:
    if stage.status == RaceStatus.not_started and as_utc(stage.datetime_start) <= now_utc():
        stage.status = RaceStatus.ongoing
        return True
    return False


def can_manage_championship(user: User | None) -> bool:
    return user is not None and user.role in {Role.admin, Role.moder} and user.status == UserStatus.active


def score_for_position(system: ChampionshipScoringSystem, position: int, participant_count: int) -> int:
    if system == ChampionshipScoringSystem.fia:
        return FIA_POINTS.get(position, 0)
    if system == ChampionshipScoringSystem.endurance:
        return ENDURANCE_POINTS.get(position, 0)
    return max(0, participant_count - position + 2)


def user_payload(user: User, team_name: str | None = None) -> dict:
    return {
        "id": user.id,
        "login": user.login,
        "nickname": user.nickname,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "pilot_number": user.pilot_number,
        "country": user.country,
        "sr": float(user.sr),
        "rating": int(round(float(user.rating))),
        "rating_race_count": int(user.rating_race_count or 0),
        "team_id": user.team_id,
        "team_name": team_name,
        "avatar_color": user.avatar_color,
        "avatar_url": user.avatar_url,
        "games": user.games or [],
        "created_at": user.created_at,
    }


def race_registration_payload(registration: RaceRegistration, user: User, team_name: str | None = None) -> dict:
    data = user_payload(user, team_name)
    data.update(
        {
            "user_id": registration.user_id,
            "car_model": registration.car_model,
            "pilot_number": registration.pilot_number,
            "registered_at": registration.registered_at.isoformat(),
            "steam_id": user.steam_id,
        }
    )
    return data


async def attach_registered_pilots(session: AsyncSession, races: list[Race]) -> None:
    race_ids = [race.id for race in races]
    if not race_ids:
        return
    grouped: dict[int, list[dict]] = {race_id: [] for race_id in race_ids}
    rows = (
        await session.execute(
            select(RaceRegistration, User, Team.name)
            .join(User, User.id == RaceRegistration.user_id)
            .outerjoin(Team, Team.id == User.team_id)
            .where(RaceRegistration.race_id.in_(race_ids))
            .order_by(RaceRegistration.race_id, RaceRegistration.registered_at, RaceRegistration.id)
        )
    ).all()
    for registration, user, team_name in rows:
        grouped.setdefault(registration.race_id, []).append(race_registration_payload(registration, user, team_name))
    for race in races:
        set_committed_value(race, "registered_pilots", grouped.get(race.id, []))


async def championship_registration_rows(session: AsyncSession, championship_id: int) -> list[tuple[ChampionshipRegistration, User, str | None]]:
    return (
        await session.execute(
            select(ChampionshipRegistration, User, Team.name)
            .join(User, User.id == ChampionshipRegistration.user_id)
            .outerjoin(Team, Team.id == User.team_id)
            .where(ChampionshipRegistration.championship_id == championship_id)
            .order_by(ChampionshipRegistration.created_at, ChampionshipRegistration.id)
        )
    ).all()


def result_position(row: dict, fallback: int) -> int:
    value = row.get("position")
    try:
        position = int(value)
    except (TypeError, ValueError):
        return fallback
    return position if position > 0 else fallback


def build_standings(championship: Championship, stages: list[Race], registration_rows: list[tuple[ChampionshipRegistration, User, str | None]]) -> list[dict]:
    approved_users: dict[int, tuple[ChampionshipRegistration, User, str | None]] = {
        registration.user_id: (registration, user, team_name)
        for registration, user, team_name in registration_rows
        if registration.status == TeamApplicationStatus.approved
    }
    standings: dict[int, dict] = {}
    for user_id, (registration, user, team_name) in approved_users.items():
        standings[user_id] = {
            "user_id": user.id,
            "login": user.login,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "nickname": user.nickname,
            "pilot_number": registration.pilot_number,
            "team_id": user.team_id,
            "team_name": team_name,
            "avatar_color": user.avatar_color,
            "avatar_url": user.avatar_url,
            "rating": int(round(float(user.rating))),
            "sr": float(user.sr),
            "points": 0,
            "pole_points": 0,
            "starts": 0,
            "best_finish": None,
        }

    for stage in stages:
        if stage.status != RaceStatus.finished or stage.results is None:
            continue
        rows = [row for row in result_rows(stage.results) if row.get("user_id") in approved_users and row.get("status") != "missing"]
        rows.sort(key=lambda row: result_position(row, 9999))
        participant_count = len(rows)
        for fallback, row in enumerate(rows, start=1):
            user_id = int(row["user_id"])
            item = standings.get(user_id)
            if item is None:
                continue
            position = result_position(row, fallback)
            item["points"] += score_for_position(stage.scoring_system, position, participant_count)
            item["starts"] += 1
            item["best_finish"] = position if item["best_finish"] is None else min(item["best_finish"], position)
            if stage.pole_bonus_enabled and row.get("qualification_position") == 1:
                item["points"] += 1
                item["pole_points"] += 1

    return sorted(standings.values(), key=lambda item: (-item["points"], item["best_finish"] or 9999, item["pilot_number"], item["user_id"]))


async def ensure_championship_pilot_number_available(
    session: AsyncSession,
    championship_id: int,
    pilot_number: int,
    exclude_registration_id: int | None = None,
) -> None:
    stmt = select(ChampionshipRegistration.id).where(
        ChampionshipRegistration.championship_id == championship_id,
        ChampionshipRegistration.pilot_number == pilot_number,
        ChampionshipRegistration.status != TeamApplicationStatus.rejected,
    )
    if exclude_registration_id is not None:
        stmt = stmt.where(ChampionshipRegistration.id != exclude_registration_id)
    if await session.scalar(stmt):
        raise HTTPException(status_code=409, detail="Pilot number is already taken in this championship")


def cars_for_championship(championship: Championship, race_assets) -> list[str]:
    if championship.game not in RACE_ASSET_GAMES:
        return []
    class_names = {item.lower() for item in championship.classes}
    cars: list[str] = []
    seen: set[str] = set()
    for asset_class in assets_for_game(race_assets, championship.game).classes:
        if asset_class.name.lower() not in class_names:
            continue
        for car in asset_class.cars:
            key = car.lower()
            if key not in seen:
                seen.add(key)
                cars.append(car)
    return cars


def validate_championship_car(car_model: str | None, allowed_cars: list[str]) -> str:
    car = (car_model or "").strip()
    if not car:
        raise HTTPException(status_code=400, detail="Car is required")
    if allowed_cars and car.lower() not in {item.lower() for item in allowed_cars}:
        raise HTTPException(status_code=400, detail="Car is not allowed")
    return car


async def auto_register_to_stage(session: AsyncSession, stage: Race, user_id: int, car_model: str, pilot_number: int) -> None:
    existing = await session.scalar(select(RaceRegistration).where(RaceRegistration.race_id == stage.id, RaceRegistration.user_id == user_id))
    if existing is not None:
        existing.car_model = car_model
        existing.pilot_number = pilot_number
        return
    count = await session.scalar(select(func.count()).select_from(RaceRegistration).where(RaceRegistration.race_id == stage.id))
    if (count or 0) >= stage.max_pilots:
        raise HTTPException(status_code=409, detail=f"Stage {stage.name} is full")
    session.add(RaceRegistration(race_id=stage.id, user_id=user_id, car_model=car_model, pilot_number=pilot_number, registered_at=now_utc()))


async def sync_approved_participant(session: AsyncSession, championship: Championship, registration: ChampionshipRegistration) -> None:
    stages = list(
        (
            await session.scalars(
                select(Race).where(Race.championship_id == championship.id).order_by(Race.championship_round.asc(), Race.datetime_start.asc())
            )
        ).all()
    )
    car_model = (registration.car_model or "TBD").strip() or "TBD"
    registration.car_model = car_model
    for stage in stages:
        await auto_register_to_stage(session, stage, registration.user_id, car_model, registration.pilot_number)


async def remove_participant_from_stages(session: AsyncSession, championship_id: int, user_id: int) -> None:
    stage_ids = list((await session.scalars(select(Race.id).where(Race.championship_id == championship_id))).all())
    if not stage_ids:
        return
    registrations = (
        await session.scalars(
            select(RaceRegistration).where(RaceRegistration.race_id.in_(stage_ids), RaceRegistration.user_id == user_id)
        )
    ).all()
    for registration in registrations:
        await session.delete(registration)


def create_stage(championship: Championship, payload: ChampionshipStageAdd | None, round_number: int, creator_id: int, allowed_cars: list[str] | None = None) -> Race:
    start = payload.datetime_start if payload else championship.championship_start
    name = (payload.name or f"{championship.name} R{round_number}").strip() if payload else f"{championship.name} R{round_number}"
    track = (payload.track or "TBA").strip() if payload else "TBA"
    server_link = (payload.server_link or "").strip() if payload else ""
    primary_class = championship.classes[0] if championship.classes else "Championship"
    return Race(
        name=name,
        description=championship.description,
        server_link=server_link,
        datetime_start=start,
        datetime_end=start + timedelta(hours=2),
        max_pilots=500,
        car_class=primary_class,
        track=track,
        mods_pack=[],
        allowed_cars=allowed_cars or [],
        status=RaceStatus.not_started,
        is_passed=False,
        results=None,
        rating_applied=False,
        video_url=None,
        video_filename=None,
        fan_vote_options=[],
        game=championship.game,
        has_qualification=payload.has_qualification if payload else True,
        scoring_system=payload.scoring_system if payload else championship.scoring_system,
        pole_bonus_enabled=payload.pole_bonus_enabled if payload else championship.pole_bonus_enabled,
        championship_id=championship.id,
        championship_round=round_number,
        creator_id=creator_id,
        is_official=True,
        registered_pilots=[],
    )


async def sync_championship_settings_to_stages(session: AsyncSession, championship: Championship) -> None:
    stages = list((await session.scalars(select(Race).where(Race.championship_id == championship.id))).all())
    primary_class = championship.classes[0] if championship.classes else "Championship"
    race_assets = await get_race_assets(session)
    allowed_cars = cars_for_championship(championship, race_assets)
    for stage in stages:
        stage.description = championship.description
        stage.game = championship.game
        stage.car_class = primary_class
        stage.allowed_cars = allowed_cars

    registrations = (
        await session.scalars(
            select(ChampionshipRegistration).where(
                ChampionshipRegistration.championship_id == championship.id,
                ChampionshipRegistration.status == TeamApplicationStatus.approved,
            )
        )
    ).all()
    for registration in registrations:
        car_model = (registration.car_model or "TBD").strip() or "TBD"
        for stage in stages:
            await auto_register_to_stage(session, stage, registration.user_id, car_model, registration.pilot_number)


def validate_championship_dates(championship: Championship) -> None:
    if championship.registration_end <= championship.registration_start:
        raise HTTPException(status_code=400, detail="Registration end must be after registration start")
    if championship.championship_end <= championship.championship_start:
        raise HTTPException(status_code=400, detail="Championship end must be after championship start")
    if championship.registration_end > championship.championship_end:
        raise HTTPException(status_code=400, detail="Registration must end before the championship ends")


async def serialize_championship(session: AsyncSession, championship: Championship, current_user: User | None = None) -> dict:
    stages = list(
        (
            await session.scalars(
                select(Race).where(Race.championship_id == championship.id).order_by(Race.championship_round.asc(), Race.datetime_start.asc())
            )
        ).all()
    )
    changed = False
    for stage in stages:
        changed = update_stage_time_status(stage) or changed
    if changed:
        await session.commit()
    await attach_registered_pilots(session, stages)
    registrations = await championship_registration_rows(session, championship.id)
    current_status = championship_status(championship)
    my_registration = next((registration for registration, _, _ in registrations if registration.user_id == current_user.id), None) if current_user else None
    participant_count = sum(1 for registration, _, _ in registrations if registration.status == TeamApplicationStatus.approved)
    pending_count = sum(1 for registration, _, _ in registrations if registration.status == TeamApplicationStatus.pending)
    public_registrations = [
        {
            "id": registration.id,
            "championship_id": registration.championship_id,
            "user_id": registration.user_id,
            "status": registration.status,
            "car_model": registration.car_model,
            "pilot_number": registration.pilot_number,
            "created_at": registration.created_at,
            "updated_at": registration.updated_at,
            "resolved_at": registration.resolved_at,
            "resolved_by": registration.resolved_by,
            "user": user_payload(user, team_name),
        }
        for registration, user, team_name in registrations
        if can_manage_championship(current_user) or registration.status == TeamApplicationStatus.approved or registration.user_id == getattr(current_user, "id", None)
    ]
    return {
        "id": championship.id,
        "name": championship.name,
        "description": championship.description,
        "classes": championship.classes or [],
        "registration_start": championship.registration_start,
        "registration_end": championship.registration_end,
        "championship_start": championship.championship_start,
        "championship_end": championship.championship_end,
        "video_url": championship.video_url,
        "game": championship.game,
        "car_change_allowed": championship.car_change_allowed,
        "scoring_system": championship.scoring_system,
        "pole_bonus_enabled": championship.pole_bonus_enabled,
        "is_published": championship.is_published,
        "creator_id": championship.creator_id,
        "status": current_status,
        "can_apply": bool(
            current_user
            and current_user.status == UserStatus.active
            and current_status == "registration_open"
            and my_registration is None
        ),
        "my_registration_status": my_registration.status if my_registration else None,
        "participant_count": participant_count,
        "pending_count": pending_count,
        "stages": stages,
        "registrations": public_registrations,
        "standings": build_standings(championship, stages, registrations),
        "created_at": championship.created_at,
        "updated_at": championship.updated_at,
    }


async def ensure_championship(session: AsyncSession, championship_id: int) -> Championship:
    championship = await session.get(Championship, championship_id)
    if championship is None:
        raise HTTPException(status_code=404, detail="Championship not found")
    return championship


@router.get("", response_model=list[ChampionshipRead])
@limiter.limit("600/minute")
async def list_championships(
    request: Request,
    status_filter: str = "all",
    offset: int = 0,
    limit: int = 50,
    user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
):
    limit = min(limit, 100)
    current = now_utc()
    stmt = select(Championship)
    if not can_manage_championship(user):
        stmt = stmt.where(Championship.is_published.is_(True))
    if status_filter == "registration_open":
        stmt = stmt.where(
            Championship.is_published.is_(True),
            Championship.registration_start <= current,
            Championship.registration_end >= current,
        )
    elif status_filter == "active":
        stmt = stmt.where(
            Championship.is_published.is_(True),
            Championship.registration_start <= current,
            Championship.championship_end >= current,
        )
    elif status_filter == "inactive":
        stmt = stmt.where(
            or_(
                Championship.is_published.is_(False),
                Championship.registration_start > current,
                Championship.championship_end < current,
            )
        )
    stmt = stmt.order_by(Championship.registration_start.desc(), Championship.id.desc()).offset(offset).limit(limit)
    championships = list((await session.scalars(stmt)).all())
    return [await serialize_championship(session, championship, user) for championship in championships]


@router.post("", response_model=ChampionshipRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def create_championship(
    payload: ChampionshipCreate,
    request: Request,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    if payload.game not in RACE_GAMES:
        raise HTTPException(status_code=400, detail="Unknown simulator")
    championship = Championship(
        name=payload.name,
        description=payload.description,
        classes=payload.classes,
        registration_start=payload.registration_start,
        registration_end=payload.registration_end,
        championship_start=payload.championship_start,
        championship_end=payload.championship_end,
        video_url=payload.video_url,
        game=payload.game,
        car_change_allowed=payload.car_change_allowed,
        default_car=None,
        scoring_system=payload.scoring_system,
        pole_bonus_enabled=payload.pole_bonus_enabled,
        is_published=payload.is_published,
        creator_id=user.id,
    )
    session.add(championship)
    await session.flush()
    race_assets = await get_race_assets(session)
    allowed_cars = cars_for_championship(championship, race_assets)
    for index, stage_payload in enumerate(payload.stages, start=1):
        session.add(create_stage(championship, stage_payload, index, user.id, allowed_cars))
    await session.commit()
    await session.refresh(championship)
    return await serialize_championship(session, championship, user)


@router.patch("/{championship_id}", response_model=ChampionshipRead)
@limiter.limit("10/minute")
async def update_championship(
    championship_id: int,
    payload: ChampionshipUpdate,
    request: Request,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    championship = await ensure_championship(session, championship_id)
    data = payload.model_dump(exclude_unset=True)
    if "game" in data and data["game"] not in RACE_GAMES:
        raise HTTPException(status_code=400, detail="Unknown simulator")
    data.pop("default_car", None)
    for field, value in data.items():
        setattr(championship, field, value)
    championship.default_car = None
    validate_championship_dates(championship)
    await sync_championship_settings_to_stages(session, championship)
    await session.commit()
    await session.refresh(championship)
    return await serialize_championship(session, championship, user)


@router.get("/{championship_id}", response_model=ChampionshipRead)
@limiter.limit("600/minute")
async def get_championship(
    championship_id: int,
    request: Request,
    user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
):
    championship = await ensure_championship(session, championship_id)
    if not championship.is_published and not can_manage_championship(user):
        raise HTTPException(status_code=404, detail="Championship not found")
    return await serialize_championship(session, championship, user)


@router.post("/{championship_id}/stages", response_model=ChampionshipRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def add_championship_stage(
    championship_id: int,
    payload: ChampionshipStageAdd,
    request: Request,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    championship = await ensure_championship(session, championship_id)
    round_number = (await session.scalar(select(func.max(Race.championship_round)).where(Race.championship_id == championship.id)) or 0) + 1
    race_assets = await get_race_assets(session)
    allowed_cars = cars_for_championship(championship, race_assets)
    stage = create_stage(championship, payload, int(round_number), user.id, allowed_cars)
    session.add(stage)
    await session.flush()
    approved = (
        await session.scalars(
            select(ChampionshipRegistration).where(
                ChampionshipRegistration.championship_id == championship.id,
                ChampionshipRegistration.status == TeamApplicationStatus.approved,
            )
        )
    ).all()
    for registration in approved:
        await auto_register_to_stage(
            session,
            stage,
            registration.user_id,
            registration.car_model or "TBD",
            registration.pilot_number,
        )
    await session.commit()
    await session.refresh(championship)
    return await serialize_championship(session, championship, user)


@router.patch("/{championship_id}/stages/{stage_id}", response_model=ChampionshipRead)
@limiter.limit("20/minute")
async def update_championship_stage(
    championship_id: int,
    stage_id: int,
    payload: ChampionshipStageUpdate,
    request: Request,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    championship = await ensure_championship(session, championship_id)
    stage = await session.get(Race, stage_id)
    if stage is None or stage.championship_id != championship.id:
        raise HTTPException(status_code=404, detail="Championship stage not found")
    data = payload.model_dump(exclude_unset=True)
    if "datetime_start" in data:
        stage.datetime_start = data["datetime_start"]
        stage.datetime_end = data["datetime_start"] + timedelta(hours=2)
    if "name" in data:
        stage.name = data["name"]
    if "track" in data:
        stage.track = data["track"] or "TBA"
    if "server_link" in data:
        stage.server_link = data["server_link"] or ""
    if "has_qualification" in data:
        stage.has_qualification = data["has_qualification"]
    if "scoring_system" in data:
        stage.scoring_system = data["scoring_system"]
    if "pole_bonus_enabled" in data:
        stage.pole_bonus_enabled = data["pole_bonus_enabled"]
    await session.commit()
    await session.refresh(championship)
    return await serialize_championship(session, championship, user)


@router.delete("/{championship_id}/stages/{stage_id}", response_model=ChampionshipRead)
@limiter.limit("10/minute")
async def delete_championship_stage(
    championship_id: int,
    stage_id: int,
    request: Request,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    championship = await ensure_championship(session, championship_id)
    stage = await session.get(Race, stage_id)
    if stage is None or stage.championship_id != championship.id:
        raise HTTPException(status_code=404, detail="Championship stage not found")
    if stage.status == RaceStatus.finished:
        raise HTTPException(status_code=400, detail="Finished championship stages cannot be deleted")
    await session.delete(stage)
    await session.commit()
    await session.refresh(championship)
    return await serialize_championship(session, championship, user)


@router.post("/{championship_id}/apply", response_model=ChampionshipRead)
@limiter.limit("30/minute")
async def apply_to_championship(
    championship_id: int,
    payload: ChampionshipApplyRequest,
    request: Request,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    championship = await ensure_championship(session, championship_id)
    if championship_status(championship) != "registration_open":
        raise HTTPException(status_code=400, detail="Championship registration is not open")
    race_assets = await get_race_assets(session)
    allowed_cars = cars_for_championship(championship, race_assets)
    car_model = validate_championship_car(payload.car_model, allowed_cars)
    existing = await session.scalar(
        select(ChampionshipRegistration).where(
            ChampionshipRegistration.championship_id == championship.id,
            ChampionshipRegistration.user_id == user.id,
        )
    )
    await ensure_championship_pilot_number_available(session, championship.id, payload.pilot_number, existing.id if existing else None)
    if existing is None:
        session.add(
            ChampionshipRegistration(
                championship_id=championship.id,
                user_id=user.id,
                status=TeamApplicationStatus.pending,
                car_model=car_model,
                pilot_number=payload.pilot_number,
            )
        )
    elif existing.status == TeamApplicationStatus.rejected:
        existing.status = TeamApplicationStatus.pending
        existing.car_model = car_model
        existing.pilot_number = payload.pilot_number
        existing.resolved_at = None
        existing.resolved_by = None
    else:
        raise HTTPException(status_code=409, detail="Championship request already exists")
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Pilot number is already taken in this championship") from exc
    await session.refresh(championship)
    return await serialize_championship(session, championship, user)


@router.patch("/{championship_id}/registrations/{registration_id}", response_model=ChampionshipRead)
@limiter.limit("20/minute")
async def moderate_championship_registration(
    championship_id: int,
    registration_id: int,
    payload: ChampionshipRegistrationModeration,
    request: Request,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    championship = await ensure_championship(session, championship_id)
    registration = await session.get(ChampionshipRegistration, registration_id)
    if registration is None or registration.championship_id != championship.id:
        raise HTTPException(status_code=404, detail="Championship request not found")
    if payload.pilot_number is not None:
        await ensure_championship_pilot_number_available(session, championship.id, payload.pilot_number, registration.id)
        registration.pilot_number = payload.pilot_number
    race_assets = await get_race_assets(session)
    allowed_cars = cars_for_championship(championship, race_assets)
    registration.status = payload.status
    registration.car_model = validate_championship_car(payload.car_model or registration.car_model, allowed_cars)
    registration.resolved_at = now_utc()
    registration.resolved_by = user.id
    if payload.status == TeamApplicationStatus.approved:
        await sync_approved_participant(session, championship, registration)
    else:
        await remove_participant_from_stages(session, championship.id, registration.user_id)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Pilot number is already taken in this championship") from exc
    await session.refresh(championship)
    return await serialize_championship(session, championship, user)


@router.post("/{championship_id}/participants", response_model=ChampionshipRead)
@limiter.limit("20/minute")
async def add_championship_participant(
    championship_id: int,
    payload: ChampionshipParticipantAdd,
    request: Request,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    championship = await ensure_championship(session, championship_id)
    pilot = await session.get(User, payload.user_id)
    if pilot is None:
        raise HTTPException(status_code=404, detail="Pilot not found")
    registration = await session.scalar(
        select(ChampionshipRegistration).where(
            ChampionshipRegistration.championship_id == championship.id,
            ChampionshipRegistration.user_id == pilot.id,
        )
    )
    await ensure_championship_pilot_number_available(session, championship.id, payload.pilot_number, registration.id if registration else None)
    race_assets = await get_race_assets(session)
    allowed_cars = cars_for_championship(championship, race_assets)
    car_model = validate_championship_car(payload.car_model, allowed_cars)
    if registration is None:
        registration = ChampionshipRegistration(
            championship_id=championship.id,
            user_id=pilot.id,
            status=TeamApplicationStatus.approved,
            car_model=car_model,
            pilot_number=payload.pilot_number,
            resolved_at=now_utc(),
            resolved_by=user.id,
        )
        session.add(registration)
    else:
        registration.status = TeamApplicationStatus.approved
        registration.car_model = car_model
        registration.pilot_number = payload.pilot_number
        registration.resolved_at = now_utc()
        registration.resolved_by = user.id
    try:
        await sync_approved_participant(session, championship, registration)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Pilot number is already taken in this championship") from exc
    await session.refresh(championship)
    return await serialize_championship(session, championship, user)


@router.patch("/{championship_id}/participants/{user_id}/car", response_model=ChampionshipRead)
@limiter.limit("20/minute")
async def update_championship_participant_car(
    championship_id: int,
    user_id: int,
    payload: ChampionshipCarUpdate,
    request: Request,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    championship = await ensure_championship(session, championship_id)
    registration = await session.scalar(
        select(ChampionshipRegistration).where(
            ChampionshipRegistration.championship_id == championship.id,
            ChampionshipRegistration.user_id == user_id,
            ChampionshipRegistration.status == TeamApplicationStatus.approved,
        )
    )
    if registration is None:
        raise HTTPException(status_code=404, detail="Championship participant not found")
    race_assets = await get_race_assets(session)
    allowed_cars = cars_for_championship(championship, race_assets)
    registration.car_model = validate_championship_car(payload.car_model, allowed_cars)
    await sync_approved_participant(session, championship, registration)
    await session.commit()
    await session.refresh(championship)
    return await serialize_championship(session, championship, user)


@router.patch("/{championship_id}/me/car", response_model=ChampionshipRead)
@limiter.limit("20/minute")
async def update_my_championship_car(
    championship_id: int,
    payload: ChampionshipCarUpdate,
    request: Request,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    championship = await ensure_championship(session, championship_id)
    if not championship.car_change_allowed:
        raise HTTPException(status_code=403, detail="Car change is locked for this championship")
    registration = await session.scalar(
        select(ChampionshipRegistration).where(
            ChampionshipRegistration.championship_id == championship.id,
            ChampionshipRegistration.user_id == user.id,
            ChampionshipRegistration.status == TeamApplicationStatus.approved,
        )
    )
    if registration is None:
        raise HTTPException(status_code=404, detail="Championship participant not found")
    race_assets = await get_race_assets(session)
    allowed_cars = cars_for_championship(championship, race_assets)
    registration.car_model = validate_championship_car(payload.car_model, allowed_cars)
    await sync_approved_participant(session, championship, registration)
    await session.commit()
    await session.refresh(championship)
    return await serialize_championship(session, championship, user)


@router.delete("/{championship_id}/participants/{user_id}", response_model=ChampionshipRead)
@limiter.limit("20/minute")
async def remove_championship_participant(
    championship_id: int,
    user_id: int,
    request: Request,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    championship = await ensure_championship(session, championship_id)
    registration = await session.scalar(
        select(ChampionshipRegistration).where(
            ChampionshipRegistration.championship_id == championship.id,
            ChampionshipRegistration.user_id == user_id,
        )
    )
    if registration is not None:
        await session.delete(registration)
    await remove_participant_from_stages(session, championship.id, user_id)
    await session.commit()
    await session.refresh(championship)
    return await serialize_championship(session, championship, user)
