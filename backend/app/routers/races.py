from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.db import get_session
from app.deps import get_optional_user, require_moder_plus, require_pilot_plus
from app.models import RACE_GAMES, Penalty, Race, RaceRegistration, RaceStatus, Role, Setup, Team, User
from app.rate_limit import limiter
from app.schemas import AccResultsUpload, ManualResultsUpload, RaceCreate, RaceManageRead, RaceRead, RaceRegisterRequest, RaceUpdate, ResultsUpload
from app.services import apply_sr_penalties, recalculate_all_ratings, recalculate_race_results, restore_race_sr_bonus, restore_sr_penalty


router = APIRouter()

ACC_RESULT_SESSION_TYPES = {"Q", "R"}


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


def registration_to_json(registration: RaceRegistration, user: User | None = None, team_name: str | None = None) -> dict:
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
                "steam_id": user.steam_id,
                "country": user.country,
                "sr": float(user.sr),
                "rating": int(round(float(user.rating))),
                "rating_race_count": user.rating_race_count,
                "team_id": user.team_id,
                "team_name": team_name,
                "avatar_color": user.avatar_color,
                "avatar_url": user.avatar_url,
                "games": user.games or [],
            }
        )
    return data


def normalize_acc_player_id(value: str | None) -> str:
    raw = str(value or "").strip()
    if raw.upper().startswith("S") and raw[1:].isdigit():
        return raw[1:]
    return raw


def acc_player_id(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.upper().startswith("S"):
        return raw
    return f"S{raw}" if raw.isdigit() else raw


def short_driver_name(user: User) -> str:
    letters = "".join(char for char in (user.nickname or user.login).upper() if char.isalnum())
    return (letters[:3] or f"P{user.pilot_number}")[:3]


def acc_forced_car_model(car_model: str | None) -> int:
    try:
        return int(str(car_model or "").strip())
    except ValueError:
        return -1


def acc_entrylist_entry(registration: RaceRegistration, user: User) -> dict:
    return {
        "drivers": [
            {
                "firstName": user.first_name,
                "lastName": user.last_name,
                "nickName": user.nickname,
                "shortName": short_driver_name(user),
                "nationality": 0,
                "driverCategory": 1,
                "helmetTemplateKey": 500,
                "helmetBaseColor": 0,
                "helmetDetailColor": 0,
                "helmetMaterialType": 0,
                "helmetGlassColor": 0,
                "helmetGlassMetallic": 0.0,
                "glovesTemplateKey": 0,
                "suitTemplateKey": 500,
                "suitDetailColor1": 0,
                "suitDetailColor2": 0,
                "playerID": acc_player_id(user.steam_id),
                "aiSkill": 100,
                "aiAggro": 50,
                "aiRainSkill": 50,
                "aiConsistency": 50,
            }
        ],
        "customCar": "",
        "raceNumber": user.pilot_number,
        "defaultGridPosition": -1,
        "forcedCarModel": acc_forced_car_model(registration.car_model),
        "overrideDriverInfo": 1,
        "isServerAdmin": 0,
        "overrideCarModelForCustomCar": 1,
        "configVersion": 1,
    }


async def get_registration_rows(session: AsyncSession, race_id: int) -> list[tuple[RaceRegistration, User]]:
    return list(
        (
            await session.execute(
                select(RaceRegistration, User)
                .join(User, User.id == RaceRegistration.user_id)
                .where(RaceRegistration.race_id == race_id)
                .order_by(RaceRegistration.registered_at, RaceRegistration.id)
            )
        ).all()
    )


async def build_acc_entrylist(session: AsyncSession, race_id: int) -> dict:
    rows = await get_registration_rows(session, race_id)
    return {
        "entries": [acc_entrylist_entry(registration, user) for registration, user in rows],
        "configVersion": 1,
        "forceEntryList": 0,
    }


def validate_acc_session(payload: dict, expected_type: str) -> None:
    session_type = str(payload.get("sessionType", "")).upper()
    if session_type not in ACC_RESULT_SESSION_TYPES:
        raise HTTPException(status_code=400, detail="Invalid ACC result JSON")
    if session_type != expected_type:
        raise HTTPException(status_code=400, detail=f"Expected ACC {expected_type} result JSON")
    result = payload.get("sessionResult")
    if not isinstance(result, dict) or not isinstance(result.get("leaderBoardLines"), list):
        raise HTTPException(status_code=400, detail="ACC result JSON must include sessionResult.leaderBoardLines")


def acc_line_driver(line: dict) -> dict:
    current = line.get("currentDriver")
    if isinstance(current, dict) and current:
        return current
    drivers = line.get("car", {}).get("drivers", [])
    return drivers[0] if drivers and isinstance(drivers[0], dict) else {}


def acc_line_player_id(line: dict) -> str:
    driver = acc_line_driver(line)
    return normalize_acc_player_id(driver.get("playerId") or driver.get("playerID"))


def acc_line_race_number(line: dict) -> int | None:
    race_number = line.get("car", {}).get("raceNumber")
    return int(race_number) if isinstance(race_number, int) else None


def acc_line_name(line: dict) -> str:
    driver = acc_line_driver(line)
    return " ".join(str(driver.get(part) or "").strip() for part in ("firstName", "lastName")).strip() or str(driver.get("shortName") or "")


def acc_best_lap_map(qualification_results: dict | None) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not qualification_results:
        return rows
    for position, line in enumerate(qualification_results["sessionResult"]["leaderBoardLines"], start=1):
        player_id = acc_line_player_id(line)
        if not player_id:
            continue
        timing = line.get("timing") or {}
        rows[player_id] = {
            "qualification_position": position,
            "qualification_best_lap_ms": timing.get("bestLap"),
        }
    return rows


def user_lookup_maps(rows: list[tuple[RaceRegistration, User]]) -> tuple[dict[str, User], dict[int, User]]:
    by_steam: dict[str, User] = {}
    by_number: dict[int, User] = {}
    for _, user in rows:
        normalized = normalize_acc_player_id(user.steam_id)
        if normalized:
            by_steam[normalized] = user
        by_number[user.pilot_number] = user
    return by_steam, by_number


def acc_line_user(line: dict, users_by_steam: dict[str, User], users_by_number: dict[int, User]) -> User | None:
    player_id = acc_line_player_id(line)
    if player_id:
        return users_by_steam.get(player_id)
    race_number = acc_line_race_number(line)
    return users_by_number.get(race_number) if race_number is not None else None


def acc_line_label(line: dict, position: int) -> str:
    player_id = acc_player_id(acc_line_player_id(line))
    race_number = acc_line_race_number(line)
    parts = [f"#{position}"]
    name = acc_line_name(line)
    if name:
        parts.append(name)
    if race_number is not None:
        parts.append(f"car {race_number}")
    if player_id:
        parts.append(player_id)
    return " / ".join(parts)


def ensure_acc_lines_are_registered(session_name: str, payload: dict, users_by_steam: dict[str, User], users_by_number: dict[int, User]) -> None:
    missing: list[str] = []
    for position, line in enumerate(payload["sessionResult"]["leaderBoardLines"], start=1):
        user = acc_line_user(line, users_by_steam, users_by_number)
        if user is None:
            missing.append(acc_line_label(line, position))
    if missing:
        preview = "; ".join(missing[:8])
        suffix = f"; +{len(missing) - 8} more" if len(missing) > 8 else ""
        raise HTTPException(status_code=400, detail=f"ACC {session_name} JSON contains pilots who are not registered for this race: {preview}{suffix}")


def build_acc_results_payload(race: Race, qualification_results: dict | None, race_results: dict, rows: list[tuple[RaceRegistration, User]]) -> dict:
    if race.has_qualification and qualification_results is None:
        raise HTTPException(status_code=400, detail="Qualification results JSON is required for this race")
    if qualification_results is not None:
        validate_acc_session(qualification_results, "Q")
    validate_acc_session(race_results, "R")
    users_by_steam, users_by_number = user_lookup_maps(rows)
    if qualification_results is not None:
        ensure_acc_lines_are_registered("qualification", qualification_results, users_by_steam, users_by_number)
    ensure_acc_lines_are_registered("race", race_results, users_by_steam, users_by_number)
    qualification_by_player = acc_best_lap_map(qualification_results)

    result_rows: list[dict] = []
    matched_user_ids: set[int] = set()
    for raw_position, line in enumerate(race_results["sessionResult"]["leaderBoardLines"], start=1):
        player_id = acc_line_player_id(line)
        race_number = acc_line_race_number(line)
        user = acc_line_user(line, users_by_steam, users_by_number)
        timing = line.get("timing") or {}
        finish_ms = timing.get("totalTime")
        driver_total_times = line.get("driverTotalTimes") if isinstance(line.get("driverTotalTimes"), list) else []
        qualification = qualification_by_player.get(player_id, {})
        row = {
            "user_id": user.id if user else None,
            "login": user.login if user else None,
            "nickname": user.nickname if user else None,
            "driver_name": acc_line_name(line),
            "player_id": acc_player_id(player_id),
            "race_number": race_number,
            "car_model": line.get("car", {}).get("carModel"),
            "finish_ms": int(finish_ms) if isinstance(finish_ms, (int, float)) else None,
            "driver_total_time_ms": int(driver_total_times[0]) if driver_total_times else None,
            "lap_count": int(timing.get("lapCount") or 0),
            "best_lap_ms": timing.get("bestLap"),
            "qualification_position": qualification.get("qualification_position"),
            "qualification_best_lap_ms": qualification.get("qualification_best_lap_ms"),
            "raw_position": raw_position,
            "source": "acc",
        }
        if user is not None:
            matched_user_ids.add(user.id)
        result_rows.append(row)

    for _, user in rows:
        if user.id not in matched_user_ids:
            result_rows.append(
                {
                    "user_id": user.id,
                    "login": user.login,
                    "nickname": user.nickname,
                    "driver_name": f"{user.first_name} {user.last_name}".strip() or user.nickname,
                    "player_id": acc_player_id(user.steam_id),
                    "race_number": user.pilot_number,
                    "finish_ms": None,
                    "lap_count": 0,
                    "best_lap_ms": None,
                    "qualification_position": None,
                    "qualification_best_lap_ms": None,
                    "raw_position": None,
                    "source": "acc",
                    "status": "missing",
                }
            )

    return {
        "format": "acc",
        "track": race_results.get("trackName") or race.track,
        "qualification_enabled": race.has_qualification,
        "qualification": (
            {
                "session_type": qualification_results.get("sessionType"),
                "raw": qualification_results,
            }
            if qualification_results is not None
            else None
        ),
        "race": {
            "session_type": race_results.get("sessionType"),
            "raw": race_results,
        },
        "rows": result_rows,
    }


def build_manual_results_payload(race: Race, payload: ManualResultsUpload, registered: list[dict]) -> dict:
    registered_by_id = {int(item["user_id"]): item for item in registered if item.get("user_id") is not None}
    rows: list[dict] = []
    seen: set[int] = set()
    for row in payload.rows:
        if row.user_id not in registered_by_id:
            raise HTTPException(status_code=400, detail=f"Pilot {row.user_id} is not registered for this race")
        pilot = registered_by_id[row.user_id]
        seen.add(row.user_id)
        rows.append(
            {
                "user_id": row.user_id,
                "login": pilot.get("login"),
                "nickname": pilot.get("nickname"),
                "driver_name": " ".join(filter(None, [pilot.get("first_name"), pilot.get("last_name")])) or pilot.get("nickname"),
                "finish_ms": row.finish_ms,
                "lap_count": row.lap_count,
                "best_lap_ms": row.best_lap_ms,
                "source": "manual",
            }
        )
    for user_id, pilot in registered_by_id.items():
        if user_id not in seen:
            rows.append(
                {
                    "user_id": user_id,
                    "login": pilot.get("login"),
                    "nickname": pilot.get("nickname"),
                    "driver_name": " ".join(filter(None, [pilot.get("first_name"), pilot.get("last_name")])) or pilot.get("nickname"),
                    "finish_ms": None,
                    "lap_count": 0,
                    "best_lap_ms": None,
                    "source": "manual",
                    "status": "missing",
                }
            )
    return {"format": "manual", "track": race.track, "qualification_enabled": race.has_qualification, "rows": rows}


async def get_registered_pilots(session: AsyncSession, race_id: int) -> list[dict]:
    rows = (
        await session.execute(
            select(RaceRegistration, User, Team.name)
            .join(User, User.id == RaceRegistration.user_id)
            .outerjoin(Team, Team.id == User.team_id)
            .where(RaceRegistration.race_id == race_id)
            .order_by(RaceRegistration.registered_at, RaceRegistration.id)
        )
    ).all()
    return [registration_to_json(registration, user, team_name) for registration, user, team_name in rows]


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
        grouped.setdefault(registration.race_id, []).append(registration_to_json(registration, user, team_name))
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
    elif status_filter == "not_finished":
        stmt = stmt.where(Race.status != RaceStatus.finished)
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
    if status_filter == "not_finished":
        stmt = stmt.where(Race.status != RaceStatus.finished)
    elif status_filter in RaceStatus._value2member_map_:
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
            "has_qualification": race.has_qualification,
            "rating_applied": race.rating_applied,
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
    requested_status = data.get("status")
    requested_results = data.get("results")
    was_finished = race.status == RaceStatus.finished
    will_be_finished = data.get("status", race.status) == RaceStatus.finished
    if "datetime_end" in data or "datetime_start" in data:
        start = data.get("datetime_start", race.datetime_start)
        end = data.get("datetime_end", race.datetime_end)
        if end <= start:
            raise HTTPException(status_code=400, detail="Registration end must be after start")
    if requested_status == RaceStatus.finished and requested_results is None and race.results is None:
        raise HTTPException(status_code=400, detail="Upload race results before finishing the race")
    if was_finished and (requested_results is not None or not will_be_finished):
        await restore_race_sr_bonus(session, race)
    for field, value in data.items():
        setattr(race, field, value)
    if race.status == RaceStatus.finished:
        race.is_passed = True
        await apply_sr_penalties(session, race)
    await recalculate_race_results(session, race)
    await recalculate_all_ratings(session)
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
    if race.results is None:
        raise HTTPException(status_code=400, detail="Upload race results before closing the race")
    if race.status != RaceStatus.finished:
        race.status = RaceStatus.finished
        race.is_passed = True
        await recalculate_race_results(session, race)
        await apply_sr_penalties(session, race)
        await recalculate_all_ratings(session)
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
    await restore_race_sr_bonus(session, race)
    setups = (await session.scalars(select(Setup).where(Setup.race_id == race.id))).all()
    for setup in setups:
        setup.race_id = None
    await session.delete(race)
    await recalculate_all_ratings(session)
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
    if race.game == "ACC":
        return await build_acc_entrylist(session, race.id)
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
    if race.game == "ACC":
        raise HTTPException(status_code=400, detail="Use ACC qualification and race JSON upload for ACC races")
    if race.status == RaceStatus.finished:
        await restore_race_sr_bonus(session, race)
    race.results = payload.results
    race.status = RaceStatus.finished
    race.is_passed = True
    await recalculate_race_results(session, race)
    await apply_sr_penalties(session, race)
    await recalculate_all_ratings(session)
    await session.commit()
    await session.refresh(race)
    await attach_registered_pilots(session, [race])
    return race


@router.post("/{race_id}/results/acc", response_model=RaceRead)
@limiter.limit("3/minute")
async def upload_acc_results(
    race_id: int,
    request: Request,
    payload: AccResultsUpload,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    ensure_can_manage_race(user, race, "upload ACC results to")
    if race.game != "ACC":
        raise HTTPException(status_code=400, detail="ACC result JSON can only be uploaded for ACC races")
    registration_rows = await get_registration_rows(session, race.id)
    if race.status == RaceStatus.finished:
        await restore_race_sr_bonus(session, race)
    race.results = build_acc_results_payload(race, payload.qualification_results, payload.race_results, registration_rows)
    race.status = RaceStatus.finished
    race.is_passed = True
    await recalculate_race_results(session, race)
    await apply_sr_penalties(session, race)
    await recalculate_all_ratings(session)
    await session.commit()
    await session.refresh(race)
    await attach_registered_pilots(session, [race])
    return race


@router.post("/{race_id}/results/manual", response_model=RaceRead)
@limiter.limit("3/minute")
async def upload_manual_results(
    race_id: int,
    request: Request,
    payload: ManualResultsUpload,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    ensure_can_manage_race(user, race, "upload manual results to")
    if race.game == "ACC":
        raise HTTPException(status_code=400, detail="Use ACC result JSON upload for ACC races")
    registered = await get_registered_pilots(session, race.id)
    if race.status == RaceStatus.finished:
        await restore_race_sr_bonus(session, race)
    race.results = build_manual_results_payload(race, payload, registered)
    race.status = RaceStatus.finished
    race.is_passed = True
    await recalculate_race_results(session, race)
    await apply_sr_penalties(session, race)
    await recalculate_all_ratings(session)
    await session.commit()
    await session.refresh(race)
    await attach_registered_pilots(session, [race])
    return race
