from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.db import get_session
from app.deps import get_optional_user, require_moder_plus, require_pilot_plus
from app.models import RACE_GAMES, Penalty, Race, RaceRegistration, RaceStatus, Role, Setup, User
from app.rate_limit import limiter
from app.schemas import RaceCreate, RaceManageRead, RaceRead, RaceRegisterRequest, RaceUpdate, ResultsUpload
from app.services import apply_sr_penalties, recalculate_race_results, restore_sr_penalty


router = APIRouter()


def update_time_based_status(race: Race) -> None:
    now = datetime.now(timezone.utc)
    if race.status == RaceStatus.registration_open and race.datetime_end <= now:
        race.status = RaceStatus.ongoing


async def ensure_race(session: AsyncSession, race_id: int) -> Race:
    race = await session.get(Race, race_id)
    if race is None:
        raise HTTPException(status_code=404, detail="Race not found")
    update_time_based_status(race)
    return race


def ensure_can_manage_race(user: User, race: Race, action: str) -> None:
    if user.role != Role.admin and race.creator_id != user.id and user.role != Role.moder:
        raise HTTPException(status_code=403, detail=f"Only creator, moder or admin can {action} this race")


def registration_to_json(registration: RaceRegistration, user: User | None = None) -> dict:
    data = {
        "user_id": registration.user_id,
        "car_model": registration.car_model,
        "registered_at": registration.registered_at.isoformat(),
    }
    if user is not None:
        data.update(
            {
                "login": user.login,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "nickname": user.nickname,
                "pilot_number": user.pilot_number,
                "country": user.country,
                "sr": float(user.sr),
                "avatar_color": user.avatar_color,
                "games": user.games or [],
            }
        )
    return data


async def get_registered_pilots(session: AsyncSession, race_id: int) -> list[dict]:
    rows = (
        await session.execute(
            select(RaceRegistration, User)
            .join(User, User.id == RaceRegistration.user_id)
            .where(RaceRegistration.race_id == race_id)
            .order_by(RaceRegistration.registered_at, RaceRegistration.id)
        )
    ).all()
    return [registration_to_json(registration, user) for registration, user in rows]


async def attach_registered_pilots(session: AsyncSession, races: list[Race]) -> None:
    race_ids = [race.id for race in races]
    if not race_ids:
        return

    grouped: dict[int, list[dict]] = {race_id: [] for race_id in race_ids}
    rows = (
        await session.execute(
            select(RaceRegistration, User)
            .join(User, User.id == RaceRegistration.user_id)
            .where(RaceRegistration.race_id.in_(race_ids))
            .order_by(RaceRegistration.race_id, RaceRegistration.registered_at, RaceRegistration.id)
        )
    ).all()
    for registration, user in rows:
        grouped.setdefault(registration.race_id, []).append(registration_to_json(registration, user))
    for race in races:
        set_committed_value(race, "registered_pilots", grouped.get(race.id, []))


@router.get("", response_model=list[RaceRead])
@limiter.limit("1200/minute")
async def list_races(
    request: Request,
    status_filter: str = "all",
    game_filter: str = "all",
    my_games_only: bool = False,
    offset: int = 0,
    limit: int = 50,
    user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
):
    limit = min(limit, 100)
    stmt = select(Race)
    if status_filter == "upcoming":
        stmt = stmt.where(Race.status == RaceStatus.registration_open)
    elif status_filter == "past":
        stmt = stmt.where(Race.status == RaceStatus.finished)
    elif status_filter in RaceStatus._value2member_map_:
        stmt = stmt.where(Race.status == RaceStatus(status_filter))
    if game_filter in RACE_GAMES:
        stmt = stmt.where(Race.game == game_filter)
    if my_games_only:
        user_games = user.games if user else []
        if not user_games:
            return []
        stmt = stmt.where(Race.game.in_(user_games))
    stmt = stmt.order_by(Race.datetime_start.desc()).offset(offset).limit(limit)
    races = list((await session.scalars(stmt)).all())
    changed = False
    for race in races:
        before = race.status
        update_time_based_status(race)
        changed = changed or before != race.status
    if changed:
        await session.commit()
    await attach_registered_pilots(session, races)
    return races


@router.get("/manage", response_model=list[RaceManageRead])
@limiter.limit("600/minute")
async def manage_races(
    request: Request,
    status_filter: str = "all",
    game_filter: str = "all",
    search: str | None = None,
    offset: int = 0,
    limit: int = 500,
    _: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    limit = min(limit, 1000)
    registered_count = func.count(RaceRegistration.id).label("registered_count")
    stmt = (
        select(Race, registered_count)
        .outerjoin(RaceRegistration, RaceRegistration.race_id == Race.id)
        .group_by(Race.id)
    )
    if status_filter in RaceStatus._value2member_map_:
        stmt = stmt.where(Race.status == RaceStatus(status_filter))
    if game_filter in RACE_GAMES:
        stmt = stmt.where(Race.game == game_filter)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                Race.name.ilike(like),
                Race.track.ilike(like),
                Race.car_class.ilike(like),
                Race.game.ilike(like),
            )
        )
    stmt = stmt.order_by(Race.datetime_start.desc()).offset(offset).limit(limit)
    rows = list((await session.execute(stmt)).all())

    changed = False
    for race, _ in rows:
        before = race.status
        update_time_based_status(race)
        changed = changed or before != race.status
    if changed:
        await session.commit()

    return [
        {
            "id": race.id,
            "name": race.name,
            "description": race.description,
            "status": race.status,
            "datetime_start": race.datetime_start,
            "datetime_end": race.datetime_end,
            "max_pilots": race.max_pilots,
            "registered_count": int(count or 0),
            "car_class": race.car_class,
            "track": race.track,
            "game": race.game,
            "creator_id": race.creator_id,
            "is_official": race.is_official,
            "created_at": race.created_at,
            "updated_at": race.updated_at,
        }
        for race, count in rows
    ]


@router.post("", response_model=RaceRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def create_race(payload: RaceCreate, request: Request, user: User = Depends(require_moder_plus), session: AsyncSession = Depends(get_session)):
    if payload.datetime_end <= payload.datetime_start:
        raise HTTPException(status_code=400, detail="Registration end must be after start")
    race = Race(
        **payload.model_dump(),
        creator_id=user.id,
        status=RaceStatus.registration_open,
        is_passed=False,
        registered_pilots=[],
    )
    session.add(race)
    await session.commit()
    await session.refresh(race)
    await attach_registered_pilots(session, [race])
    return race


@router.get("/{race_id}", response_model=RaceRead)
@limiter.limit("600/minute")
async def get_race(
    race_id: int,
    request: Request,
    _: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    await session.commit()
    await session.refresh(race)
    await attach_registered_pilots(session, [race])
    return race


@router.patch("/{race_id}", response_model=RaceRead)
@limiter.limit("3/minute")
async def update_race(
    race_id: int,
    request: Request,
    payload: RaceUpdate,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    ensure_can_manage_race(user, race, "edit")
    data = payload.model_dump(exclude_unset=True)
    if "datetime_end" in data or "datetime_start" in data:
        start = data.get("datetime_start", race.datetime_start)
        end = data.get("datetime_end", race.datetime_end)
        if end <= start:
            raise HTTPException(status_code=400, detail="Registration end must be after start")
    for field, value in data.items():
        setattr(race, field, value)
    if race.status == RaceStatus.finished:
        race.is_passed = True
        await apply_sr_penalties(session, race)
    await recalculate_race_results(session, race)
    await session.commit()
    await session.refresh(race)
    await attach_registered_pilots(session, [race])
    return race


@router.post("/{race_id}/close", response_model=RaceRead)
@limiter.limit("3/minute")
async def close_race(
    race_id: int,
    request: Request,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    ensure_can_manage_race(user, race, "close")
    if race.status != RaceStatus.finished:
        race.status = RaceStatus.finished
        race.is_passed = True
        await recalculate_race_results(session, race)
        await apply_sr_penalties(session, race)
        await session.commit()
        await session.refresh(race)
    await attach_registered_pilots(session, [race])
    return race


@router.delete("/{race_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/minute")
async def delete_race(
    race_id: int,
    request: Request,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    ensure_can_manage_race(user, race, "delete")
    penalties = (await session.scalars(select(Penalty).where(Penalty.race_id == race.id))).all()
    for penalty in penalties:
        await restore_sr_penalty(session, penalty)
    setups = (await session.scalars(select(Setup).where(Setup.race_id == race.id))).all()
    for setup in setups:
        setup.race_id = None
    await session.delete(race)
    await session.commit()


@router.post("/{race_id}/register", response_model=RaceRead)
@limiter.limit("600/minute")
async def register_for_race(
    race_id: int,
    request: Request,
    payload: RaceRegisterRequest,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Race).where(Race.id == race_id).with_for_update())
    race = result.scalar_one_or_none()
    if race is None:
        raise HTTPException(status_code=404, detail="Race not found")
    update_time_based_status(race)
    if race.status != RaceStatus.registration_open:
        raise HTTPException(status_code=400, detail="Registration is not open")
    if race.allowed_cars and payload.car_model not in race.allowed_cars:
        raise HTTPException(status_code=400, detail="Car is not allowed")

    existing = await session.scalar(
        select(RaceRegistration).where(
            RaceRegistration.race_id == race.id,
            RaceRegistration.user_id == user.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Already registered")
    registered_count = await session.scalar(select(func.count()).select_from(RaceRegistration).where(RaceRegistration.race_id == race.id))
    if (registered_count or 0) >= race.max_pilots:
        raise HTTPException(status_code=409, detail="Race is full")

    session.add(
        RaceRegistration(
            race_id=race.id,
            user_id=user.id,
            car_model=payload.car_model,
            registered_at=datetime.now(timezone.utc),
        )
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Already registered") from exc
    await session.refresh(race)
    await attach_registered_pilots(session, [race])
    return race


@router.delete("/{race_id}/register", response_model=RaceRead)
@limiter.limit("600/minute")
async def unregister_from_race(
    race_id: int,
    request: Request,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Race).where(Race.id == race_id).with_for_update())
    race = result.scalar_one_or_none()
    if race is None:
        raise HTTPException(status_code=404, detail="Race not found")
    update_time_based_status(race)
    if race.status != RaceStatus.registration_open:
        raise HTTPException(status_code=400, detail="Registration is not open")
    registration = await session.scalar(
        select(RaceRegistration).where(
            RaceRegistration.race_id == race.id,
            RaceRegistration.user_id == user.id,
        )
    )
    if registration is not None:
        await session.delete(registration)
    await session.commit()
    await session.refresh(race)
    await attach_registered_pilots(session, [race])
    return race


@router.get("/{race_id}/registered-pilots")
@limiter.limit("120/minute")
async def export_registered_pilots(
    race_id: int,
    request: Request,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    ensure_can_manage_race(user, race, "export pilots from")
    return {"race_id": race.id, "registered_pilots": await get_registered_pilots(session, race.id)}


@router.post("/{race_id}/results", response_model=RaceRead)
@limiter.limit("3/minute")
async def upload_results(
    race_id: int,
    request: Request,
    payload: ResultsUpload,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    ensure_can_manage_race(user, race, "upload results to")
    race.results = payload.results
    race.status = RaceStatus.finished
    race.is_passed = True
    await recalculate_race_results(session, race)
    await apply_sr_penalties(session, race)
    await session.commit()
    await session.refresh(race)
    await attach_registered_pilots(session, [race])
    return race
