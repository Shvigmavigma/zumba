from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import delete
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.db import get_session
from app.deps import require_admin
from app.deps import get_optional_user, require_moder_plus, require_pilot_plus
from app.models import AppSetting, RaceFanVote
from app.models import Championship, ChampionshipRegistration, RACE_GAMES, Penalty, Race, RaceRegistration, RaceStatus, Role, Setup, Team, TeamApplicationStatus, User
from app.race_assets import normalize_race_create_assets, normalize_race_update_assets
from app.race_videos import remove_race_video_file, save_race_video_file
from app.rate_limit import limiter
from app.schemas import FanVoteCast, FanVoteConfigRead, FanVoteConfigUpdate, FanVoteRead, FanVoteSetup
from app.schemas import AccResultsUpload, ManualResultsUpload, RaceCreate, RaceManageRead, RaceRead, RaceRegisterRequest, RaceUpdate, ResultsUpload
from app.services import apply_sr_penalties, recalculate_all_ratings, recalculate_race_results, restore_race_sr_bonus, restore_sr_penalty


router = APIRouter()

ACC_RESULT_SESSION_TYPES = {"Q", "R"}
ACC_CAR_MODEL_IDS = {
    "porsche991gt3r2018": 0,
    "porsche911gt3r2018": 0,
    "mercedesamggt32015": 1,
    "ferrari488gt32018": 2,
    "audir8lmsgt32015": 3,
    "audir8lms": 3,
    "lamborghinihuracangt32015": 4,
    "mclaren650sgt32015": 5,
    "nissangtrnismogt32018": 6,
    "bmwm6gt32017": 7,
    "bentleycontinentalgt32018": 8,
    "porsche911iigt3cup2017": 9,
    "nissangtrnismogt32015": 10,
    "bentleycontinentalgt32015": 11,
    "astonmartinv12vantagegt32013": 12,
    "reiterengineeringrexgt32017": 13,
    "emilfreyjaguargt32012": 14,
    "lexusrfcgt32016": 15,
    "lamborghinihuracanevogt32019": 16,
    "hondansxgt32017": 17,
    "lamborghinihuracansupertrofeo2015": 18,
    "audir8lmsevogt32019": 19,
    "astonmartinv8vantagegt32019": 20,
    "amrv8vantagegt32019": 20,
    "hondansxevogt32019": 21,
    "mclaren720sgt32019": 22,
    "porsche911iigt3r2019": 23,
    "ferrari488evogt32020": 24,
    "ferrari488gt3evo2020": 24,
    "mercedesamgevogt32020": 25,
    "mercedesamggt32020": 25,
    "mercedesamggt3": 25,
    "ferrari488challengeevo2020": 26,
    "bmwm2cs2020": 27,
    "bmwm2csracing2020": 27,
    "porsche911gt3cup9922021": 28,
    "lamborghinihuracansupertrofeoevo22021": 29,
    "bmwm4gt32021": 30,
    "bmwm4gt3": 30,
    "audir8lmsevoiigt32022": 31,
    "ferrari296gt32023": 32,
    "ferrari296gt3": 32,
    "lamborghinihuracanevo2gt32023": 33,
    "lamborghinihuracangt3evo22023": 33,
    "porsche992gt3r2023": 34,
    "porsche992gt3r": 34,
    "mclaren720sevogt32023": 35,
    "mclaren720sgt3evo2023": 35,
    "alpinea1102018": 50,
    "amrv8vantage2018": 51,
    "astonmartinv8vantagegt42018": 51,
    "audir8lms2018": 52,
    "audir8lmsgt42018": 52,
    "bmwm42018": 53,
    "bmwm4gt42018": 53,
    "chevroletcamaror2017": 55,
    "chevroletcamarogt42017": 55,
    "ginettag552012": 56,
    "ktmxbow2016": 57,
    "maseratigranturismomc2016": 58,
    "maseratimcgt42016": 58,
    "mclaren570s2016": 59,
    "mclaren570sgt42016": 59,
    "mercedesamg2016": 60,
    "mercedesamggt42016": 60,
    "porsche718caymangt4clubsport2019": 61,
    "audir8lmsgt2": 80,
    "ktmxbowgt2": 82,
    "maseratimc20gt2": 83,
    "mercedesamggt2": 84,
    "porsche911gt2rscsevokit": 85,
    "porsche9352019": 86,
}


def update_time_based_status(race: Race) -> None:
    now = datetime.now(timezone.utc)
    if race.status == RaceStatus.not_started and race.datetime_start <= now:
        race.status = RaceStatus.ongoing
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


def normalize_external_race_data(data: dict, race: Race | None = None) -> dict:
    game = data.get("game", race.game if race else None)
    if game != "LMU":
        return data
    link = str(data.get("server_link", race.server_link if race else "") or "").strip()
    if not link:
        raise HTTPException(status_code=400, detail="LMU races require an external link")
    data["server_link"] = link
    data["track"] = "LMU"
    data["car_class"] = "LMU"
    data["has_qualification"] = False
    data["mods_pack"] = []
    data["allowed_cars"] = []
    return data


FAN_VOTE_DURATION_KEY = "fan_vote_duration_hours"
DEFAULT_FAN_VOTE_DURATION_HOURS = 24
MAX_FAN_VOTE_DURATION_HOURS = 168


def clamp_fan_vote_duration(value: int) -> int:
    return max(1, min(MAX_FAN_VOTE_DURATION_HOURS, value))


def to_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def get_fan_vote_duration_hours(session: AsyncSession) -> int:
    setting = await session.get(AppSetting, FAN_VOTE_DURATION_KEY)
    raw_value = setting.value if setting is not None else {}
    if not isinstance(raw_value, dict):
        return DEFAULT_FAN_VOTE_DURATION_HOURS
    try:
        return clamp_fan_vote_duration(int(raw_value.get("hours", DEFAULT_FAN_VOTE_DURATION_HOURS)))
    except (TypeError, ValueError):
        return DEFAULT_FAN_VOTE_DURATION_HOURS


async def save_fan_vote_duration_hours(session: AsyncSession, hours: int) -> int:
    normalized_hours = clamp_fan_vote_duration(hours)
    setting = await session.get(AppSetting, FAN_VOTE_DURATION_KEY)
    if setting is None:
        setting = AppSetting(key=FAN_VOTE_DURATION_KEY, value={"hours": normalized_hours})
        session.add(setting)
    else:
        setting.value = {"hours": normalized_hours}
    await session.commit()
    return normalized_hours


def normalize_fan_vote_options(value) -> list[int]:
    options: list[int] = []
    for item in value or []:
        try:
            user_id = int(item)
        except (TypeError, ValueError):
            continue
        if user_id > 0 and user_id not in options:
            options.append(user_id)
    return options[:3]


async def build_fan_vote_payload(session: AsyncSession, race: Race, current_user: User | None) -> FanVoteRead:
    duration_hours = await get_fan_vote_duration_hours(session)
    option_ids = normalize_fan_vote_options(race.fan_vote_options)
    started_at = to_utc(race.fan_vote_started_at)
    ends_at = started_at + timedelta(hours=duration_hours) if started_at else None
    now = datetime.now(timezone.utc)

    if not option_ids:
        return FanVoteRead(enabled=False, is_open=False, show_results=False, duration_hours=duration_hours)

    count_rows = (
        await session.execute(
            select(RaceFanVote.target_id, func.count(RaceFanVote.id))
            .where(RaceFanVote.race_id == race.id, RaceFanVote.target_id.in_(option_ids))
            .group_by(RaceFanVote.target_id)
        )
    ).all()
    counts = {int(target_id): int(count) for target_id, count in count_rows}
    total_votes = sum(counts.values())

    my_vote_user_id = None
    if current_user is not None:
        my_vote_user_id = await session.scalar(
            select(RaceFanVote.target_id).where(RaceFanVote.race_id == race.id, RaceFanVote.user_id == current_user.id)
        )

    user_rows = (
        await session.execute(
            select(User, Team.name, Team.abbreviation)
            .outerjoin(Team, Team.id == User.team_id)
            .where(User.id.in_(option_ids))
        )
    ).all()
    users_by_id = {user.id: (user, team_name, team_abbreviation) for user, team_name, team_abbreviation in user_rows}
    options = []
    for user_id in option_ids:
        item = users_by_id.get(user_id)
        if item is None:
            continue
        user, team_name, team_abbreviation = item
        votes = counts.get(user.id, 0)
        options.append(
            {
                "user_id": user.id,
                "login": user.login,
                "nickname": user.nickname,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "pilot_number": user.pilot_number,
                "team_name": team_name,
                "team_abbreviation": team_abbreviation,
                "avatar_color": user.avatar_color,
                "avatar_url": user.avatar_url,
                "rating": int(round(float(user.rating))),
                "sr": float(user.sr),
                "votes": votes,
                "percentage": round(votes * 100 / total_votes, 1) if total_votes else 0,
            }
        )

    enabled = len(options) == 3 and started_at is not None
    is_open = bool(enabled and race.status == RaceStatus.finished and ends_at and ends_at > now)

    return FanVoteRead(
        enabled=enabled,
        is_open=is_open,
        show_results=bool(enabled and not is_open),
        duration_hours=duration_hours,
        started_at=started_at,
        ends_at=ends_at,
        total_votes=total_votes,
        my_vote_user_id=my_vote_user_id,
        options=options,
    )


async def ensure_fan_vote_options_are_registered(session: AsyncSession, race: Race, option_user_ids: list[int]) -> None:
    registered_ids = set(
        (
            await session.scalars(
                select(RaceRegistration.user_id).where(
                    RaceRegistration.race_id == race.id,
                    RaceRegistration.user_id.in_(option_user_ids),
                )
            )
        ).all()
    )
    missing_ids = [user_id for user_id in option_user_ids if user_id not in registered_ids]
    if missing_ids:
        raise HTTPException(status_code=400, detail=f"Fan vote pilots must be registered for this race: {', '.join(map(str, missing_ids))}")


def registration_to_json(registration: RaceRegistration, user: User | None = None, team_name: str | None = None, team_abbreviation: str | None = None) -> dict:
    data = {
        "user_id": registration.user_id,
        "car_model": registration.car_model,
        "pilot_number": registration.pilot_number,
        "registered_at": registration.registered_at.isoformat(),
    }
    if user is not None:
        data.update(
            {
                "login": user.login,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "nickname": user.nickname,
                "pilot_number": registration.pilot_number,
                "steam_id": user.steam_id,
                "country": user.country,
                "sr": float(user.sr),
                "rating": int(round(float(user.rating))),
                "rating_race_count": user.rating_race_count,
                "team_id": user.team_id,
                "team_name": team_name,
                "team_abbreviation": team_abbreviation,
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


def short_driver_name(user: User, pilot_number: int | None = None) -> str:
    letters = "".join(char for char in (user.nickname or user.login).upper() if char.isalnum())
    return (letters[:3] or f"P{pilot_number or user.pilot_number}")[:3]


def acc_forced_car_model(car_model: str | None) -> int:
    raw = str(car_model or "").strip()
    try:
        return int(raw)
    except ValueError:
        normalized = "".join(char for char in raw.lower() if char.isalnum())
        return ACC_CAR_MODEL_IDS.get(normalized, -1)


def acc_entrylist_entry(registration: RaceRegistration, user: User, car_model: str | None = None) -> dict:
    resolved_car_model = (car_model or registration.car_model or "").strip()
    return {
        "drivers": [
            {
                "firstName": user.first_name,
                "lastName": user.last_name,
                "nickName": user.nickname,
                "shortName": short_driver_name(user, registration.pilot_number),
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
        "carModel": resolved_car_model,
        "raceNumber": registration.pilot_number,
        "defaultGridPosition": -1,
        "forcedCarModel": acc_forced_car_model(resolved_car_model),
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
    race = await session.get(Race, race_id)
    rows = await get_registration_rows(session, race_id)
    championship_cars: dict[int, str] = {}
    default_car = ""
    if race and race.championship_id:
        championship_cars = dict(
            (
                await session.execute(
                    select(ChampionshipRegistration.user_id, ChampionshipRegistration.car_model).where(
                        ChampionshipRegistration.championship_id == race.championship_id,
                        ChampionshipRegistration.status == TeamApplicationStatus.approved,
                    )
                )
            ).all()
        )
        championship = await session.get(Championship, race.championship_id)
        default_car = (championship.default_car if championship else "") or ""

    def resolved_car(registration: RaceRegistration, user: User) -> str:
        car_model = (registration.car_model or "").strip()
        if car_model and car_model.upper() != "TBD":
            return car_model
        championship_car = (championship_cars.get(user.id) or "").strip()
        if championship_car and championship_car.upper() != "TBD":
            return championship_car
        return default_car

    return {
        "entries": [acc_entrylist_entry(registration, user, resolved_car(registration, user)) for registration, user in rows],
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
    for registration, user in rows:
        normalized = normalize_acc_player_id(user.steam_id)
        if normalized:
            by_steam[normalized] = user
        by_number[registration.pilot_number] = user
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
    registrations_by_user_id = {user.id: registration for registration, user in rows}
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
        registration = registrations_by_user_id.get(user.id) if user else None
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
            "race_number": race_number if race_number is not None else (registration.pilot_number if registration else None),
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

    for registration, user in rows:
        if user.id not in matched_user_ids:
            result_rows.append(
                {
                    "user_id": user.id,
                    "login": user.login,
                    "nickname": user.nickname,
                    "driver_name": f"{user.first_name} {user.last_name}".strip() or user.nickname,
                    "player_id": acc_player_id(user.steam_id),
                    "race_number": registration.pilot_number,
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
            select(RaceRegistration, User, Team.name, Team.abbreviation)
            .join(User, User.id == RaceRegistration.user_id)
            .outerjoin(Team, Team.id == User.team_id)
            .where(RaceRegistration.race_id == race_id)
            .order_by(RaceRegistration.registered_at, RaceRegistration.id)
        )
    ).all()
    return [registration_to_json(registration, user, team_name, team_abbreviation) for registration, user, team_name, team_abbreviation in rows]


async def ensure_race_pilot_number_available(session: AsyncSession, race_id: int, pilot_number: int) -> None:
    existing_id = await session.scalar(
        select(RaceRegistration.id).where(
            RaceRegistration.race_id == race_id,
            RaceRegistration.pilot_number == pilot_number,
        )
    )
    if existing_id:
        raise HTTPException(status_code=409, detail="Pilot number is already taken in this race")


async def attach_registered_pilots(session: AsyncSession, races: list[Race]) -> None:
    race_ids = [race.id for race in races]
    if not race_ids:
        return

    grouped: dict[int, list[dict]] = {race_id: [] for race_id in race_ids}
    rows = (
        await session.execute(
            select(RaceRegistration, User, Team.name, Team.abbreviation)
            .join(User, User.id == RaceRegistration.user_id)
            .outerjoin(Team, Team.id == User.team_id)
            .where(RaceRegistration.race_id.in_(race_ids))
            .order_by(RaceRegistration.race_id, RaceRegistration.registered_at, RaceRegistration.id)
        )
    ).all()
    for registration, user, team_name, team_abbreviation in rows:
        grouped.setdefault(registration.race_id, []).append(registration_to_json(registration, user, team_name, team_abbreviation))
    for race in races:
        set_committed_value(race, "registered_pilots", grouped.get(race.id, []))


@router.get("", response_model=list[RaceRead])
@limiter.limit("1200/minute")
async def list_races(
    request: Request,
    status_filter: str = "all",
    game_filter: str = "all",
    my_games_only: bool = False,
    include_championship: bool = False,
    championship_id: int | None = None,
    offset: int = 0,
    limit: int = 50,
    user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
):
    limit = min(limit, 100)
    stmt = select(Race)
    if championship_id is not None:
        stmt = stmt.where(Race.championship_id == championship_id)
    elif not include_championship:
        stmt = stmt.where(Race.championship_id.is_(None))
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
            "server_link": race.server_link,
            "status": race.status,
            "datetime_start": race.datetime_start,
            "datetime_end": race.datetime_end,
            "max_pilots": race.max_pilots,
            "registered_count": int(count or 0),
            "car_class": race.car_class,
            "track": race.track,
            "game": race.game,
            "has_qualification": race.has_qualification,
            "scoring_system": race.scoring_system,
            "pole_bonus_enabled": race.pole_bonus_enabled,
            "rating_applied": race.rating_applied,
            "championship_id": race.championship_id,
            "championship_round": race.championship_round,
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
    data = await normalize_race_create_assets(session, payload.model_dump())
    data = normalize_external_race_data(data)
    race = Race(
        **data,
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


@router.get("/fan-vote/config", response_model=FanVoteConfigRead)
@limiter.limit("600/minute")
async def get_fan_vote_config(
    request: Request,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return FanVoteConfigRead(duration_hours=await get_fan_vote_duration_hours(session))


@router.patch("/fan-vote/config", response_model=FanVoteConfigRead)
@limiter.limit("10/minute")
async def update_fan_vote_config(
    payload: FanVoteConfigUpdate,
    request: Request,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return FanVoteConfigRead(duration_hours=await save_fan_vote_duration_hours(session, payload.duration_hours))


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
    data = await normalize_race_update_assets(session, race, data)
    data = normalize_external_race_data(data, race)
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
    video_url = race.video_url
    await session.delete(race)
    await recalculate_all_ratings(session)
    await session.commit()
    remove_race_video_file(video_url)


@router.post("/{race_id}/video", response_model=RaceRead)
@limiter.limit("3/minute")
async def upload_race_video(
    race_id: int,
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    if race.status != RaceStatus.finished:
        raise HTTPException(status_code=400, detail="Video can be attached only to a finished race")
    previous_video_url = race.video_url
    new_video_url = await save_race_video_file(file, race.id)
    race.video_url = new_video_url
    race.video_filename = file.filename or "race-video"
    race.video_uploaded_at = datetime.now(timezone.utc)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        remove_race_video_file(new_video_url)
        raise
    await session.refresh(race)
    remove_race_video_file(previous_video_url)
    await attach_registered_pilots(session, [race])
    return race


@router.delete("/{race_id}/video", response_model=RaceRead)
@limiter.limit("10/minute")
async def delete_race_video(
    race_id: int,
    request: Request,
    _: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    previous_video_url = race.video_url
    race.video_url = None
    race.video_filename = None
    race.video_uploaded_at = None
    await session.commit()
    await session.refresh(race)
    remove_race_video_file(previous_video_url)
    await attach_registered_pilots(session, [race])
    return race


@router.get("/{race_id}/fan-vote", response_model=FanVoteRead)
@limiter.limit("600/minute")
async def get_race_fan_vote(
    race_id: int,
    request: Request,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    return await build_fan_vote_payload(session, race, user)


@router.patch("/{race_id}/fan-vote", response_model=FanVoteRead)
@limiter.limit("10/minute")
async def setup_race_fan_vote(
    race_id: int,
    request: Request,
    payload: FanVoteSetup,
    _: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    if race.status != RaceStatus.finished:
        raise HTTPException(status_code=400, detail="Fan vote can be started only after the race is finished")
    await ensure_fan_vote_options_are_registered(session, race, payload.option_user_ids)
    race.fan_vote_options = payload.option_user_ids
    race.fan_vote_started_at = datetime.now(timezone.utc)
    await session.execute(delete(RaceFanVote).where(RaceFanVote.race_id == race.id))
    await session.commit()
    await session.refresh(race)
    return await build_fan_vote_payload(session, race, None)


@router.post("/{race_id}/fan-vote", response_model=FanVoteRead)
@limiter.limit("60/minute")
async def cast_race_fan_vote(
    race_id: int,
    request: Request,
    payload: FanVoteCast,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    fan_vote = await build_fan_vote_payload(session, race, user)
    if not fan_vote.enabled:
        raise HTTPException(status_code=400, detail="Fan vote is not configured for this race")
    if not fan_vote.is_open:
        raise HTTPException(status_code=400, detail="Fan vote is closed")
    option_ids = {option.user_id for option in fan_vote.options}
    if payload.target_user_id not in option_ids:
        raise HTTPException(status_code=400, detail="Choose one of the fan vote pilots")

    existing_vote = await session.scalar(
        select(RaceFanVote).where(RaceFanVote.race_id == race.id, RaceFanVote.user_id == user.id)
    )
    if existing_vote is None:
        session.add(RaceFanVote(race_id=race.id, user_id=user.id, target_id=payload.target_user_id))
    else:
        existing_vote.target_id = payload.target_user_id
    await session.commit()
    return await build_fan_vote_payload(session, race, user)


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
    registration_car = payload.car_model
    registration_number = payload.pilot_number
    if race.championship_id is not None:
        if race.status != RaceStatus.not_started:
            raise HTTPException(status_code=400, detail="Championship stage registration is closed")
        championship_registration = await session.scalar(
            select(ChampionshipRegistration).where(
                ChampionshipRegistration.championship_id == race.championship_id,
                ChampionshipRegistration.user_id == user.id,
                ChampionshipRegistration.status == TeamApplicationStatus.approved,
            )
        )
        if championship_registration is None:
            raise HTTPException(status_code=403, detail="Register to the championship first")
        championship = await session.get(Championship, race.championship_id)
        registration_car = championship_registration.car_model or championship.default_car if championship else championship_registration.car_model
        registration_car = registration_car or payload.car_model or "TBD"
        registration_number = championship_registration.pilot_number
    else:
        if race.status != RaceStatus.registration_open:
            raise HTTPException(status_code=400, detail="Registration is not open")
        if registration_number is None:
            raise HTTPException(status_code=400, detail="Pilot number is required")
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
    await ensure_race_pilot_number_available(session, race.id, registration_number)
    registered_count = await session.scalar(select(func.count()).select_from(RaceRegistration).where(RaceRegistration.race_id == race.id))
    if (registered_count or 0) >= race.max_pilots:
        raise HTTPException(status_code=409, detail="Race is full")

    session.add(
        RaceRegistration(
            race_id=race.id,
            user_id=user.id,
            car_model=registration_car,
            pilot_number=registration_number,
            registered_at=datetime.now(timezone.utc),
        )
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Pilot number is already taken in this race") from exc
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
    if race.championship_id is not None:
        if race.status != RaceStatus.not_started:
            raise HTTPException(status_code=400, detail="Championship stage registration is closed")
        championship_registration = await session.scalar(
            select(ChampionshipRegistration).where(
                ChampionshipRegistration.championship_id == race.championship_id,
                ChampionshipRegistration.user_id == user.id,
                ChampionshipRegistration.status == TeamApplicationStatus.approved,
            )
        )
        if championship_registration is None:
            raise HTTPException(status_code=403, detail="Register to the championship first")
    elif race.status != RaceStatus.registration_open:
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
