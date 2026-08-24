from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import delete
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

from app.db import get_session
from app.deps import require_admin
from app.deps import get_optional_user, require_moder_plus, require_pilot_plus
from app.routers.app_settings import get_license_settings_value
from app.models import AppSetting, RaceFanVote
from app.models import Championship, ChampionshipRegistration, RACE_GAMES, Penalty, Race, RaceRegistration, RaceStatus, Role, Setup, Team, TeamApplicationStatus, TeamRaceRegistration, User, UserStatus
from app.race_assets import DEFAULT_ACC_CAR_MODEL_IDS, get_race_assets, normalize_race_create_assets, normalize_race_update_assets
from app.race_videos import remove_race_video_file, save_race_video_file
from app.rate_limit import limiter
from app.schemas import FanVoteCast, FanVoteConfigRead, FanVoteConfigUpdate, FanVoteRead, FanVoteSetup
from app.schemas import AccResultsUpload, ManualResultsUpload, RaceCreate, RaceManageRead, RaceRead, RaceRegisterRequest, RaceUpdate, ResultsUpload, TeamRaceRegisterRequest
from app.services import apply_sr_penalties, recalculate_all_ratings, recalculate_race_results, restore_race_sr_bonus, restore_sr_penalty, result_rows


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
    "lexusrcfgt32016": 15,
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
    "fordmustanggt32024": 36,
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

ACC_DRIVER_CATEGORY_BY_TIER_INDEX = (0, 0, 1, 2, 3, 3, 3)
ACC_DRIVER_CATEGORY_BY_LICENSE = {
    "rookie": 0,
    "bronze": 0,
    "silver": 1,
    "gold": 2,
    "platinum": 3,
    "diamond": 3,
    "champ": 3,
}


def acc_driver_category_for_user(user: User | dict, game: str, license_tiers: list) -> int:
    ratings = user.get("game_ratings") if isinstance(user, dict) else user.game_ratings
    ratings = ratings if isinstance(ratings, dict) else {}
    game_rating = ratings.get(game)
    if isinstance(game_rating, dict):
        raw_rating = game_rating.get("rating")
    else:
        raw_rating = None
    if raw_rating is None:
        raw_rating = user.get("rating") if isinstance(user, dict) else user.rating
    try:
        rating = float(raw_rating or 0)
    except (TypeError, ValueError):
        rating = 0

    for index, tier in enumerate(license_tiers or []):
        minimum = tier.get("min_rating") if isinstance(tier, dict) else tier.min_rating
        maximum = tier.get("max_rating") if isinstance(tier, dict) else tier.max_rating
        if minimum <= rating <= maximum:
            name = tier.get("name") if isinstance(tier, dict) else tier.name
            return ACC_DRIVER_CATEGORY_BY_LICENSE.get(
                str(name or "").strip().lower(),
                ACC_DRIVER_CATEGORY_BY_TIER_INDEX[min(index, len(ACC_DRIVER_CATEGORY_BY_TIER_INDEX) - 1)],
            )
    return 0


def scheduled_race_status(registration_start: datetime, registration_end: datetime, race_time: datetime, now: datetime | None = None) -> RaceStatus:
    current = now or datetime.now(timezone.utc)
    if to_utc(race_time) <= current:
        return RaceStatus.ongoing
    if to_utc(registration_start) <= current < to_utc(registration_end):
        return RaceStatus.registration_open
    return RaceStatus.not_started


def update_time_based_status(race: Race) -> None:
    if race.status == RaceStatus.finished:
        return
    if race.championship_id is not None:
        race.status = RaceStatus.ongoing if to_utc(race.datetime_start) <= datetime.now(timezone.utc) else RaceStatus.not_started
        return
    race.status = scheduled_race_status(race.registration_start, race.datetime_end, race.datetime_start)


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
        if "lmu_results_at" in data:
            data["lmu_results_at"] = None
        return data
    link = str(data.get("server_link", race.server_link if race else "") or "").strip()
    if not link:
        raise HTTPException(status_code=400, detail="LMU races require an external link")
    data["server_link"] = link
    lmu_results_at = data.get("lmu_results_at", race.lmu_results_at if race else None)
    if lmu_results_at is None:
        lmu_results_at = data.get("datetime_start", race.datetime_start if race else None)
    data["lmu_results_at"] = lmu_results_at
    track = str(data.get("track", race.track if race else "") or "").strip()
    car_class = str(data.get("car_class", race.car_class if race else "") or "").strip()
    if not track:
        raise HTTPException(status_code=400, detail="LMU races require a track")
    if not car_class:
        raise HTTPException(status_code=400, detail="LMU races require a class")
    data["track"] = track
    data["car_class"] = car_class
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


def race_result_user_ids(race: Race) -> set[int]:
    return {int(row["user_id"]) for row in result_rows(race.results) if row.get("user_id") is not None}


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
                "game_ratings": user.game_ratings or {},
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
    valid_ids = registered_ids | race_result_user_ids(race)
    missing_ids = [user_id for user_id in option_user_ids if user_id not in valid_ids]
    if missing_ids:
        raise HTTPException(status_code=400, detail=f"Fan vote pilots must be registered or present in race results: {', '.join(map(str, missing_ids))}")


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
                "game_ratings": user.game_ratings or {},
                "team_id": user.team_id,
                "team_name": team_name,
                "team_abbreviation": team_abbreviation,
                "avatar_color": user.avatar_color,
                "avatar_url": user.avatar_url,
                "games": user.games or [],
            }
        )
    return data


def team_registration_to_json(registration: TeamRaceRegistration, team: Team | None = None) -> dict:
    return {
        "id": registration.id,
        "race_id": registration.race_id,
        "team_id": registration.team_id,
        "team_name": team.name if team else None,
        "team_abbreviation": team.abbreviation if team else None,
        "team_avatar_color": team.avatar_color if team else None,
        "team_avatar_url": team.avatar_url if team else None,
        "car_model": registration.car_model,
        "race_number": registration.race_number,
        "drivers": registration.drivers or [],
        "registered_by": registration.registered_by,
        "registered_at": registration.registered_at.isoformat(),
        "updated_at": registration.updated_at.isoformat(),
    }


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


def acc_forced_car_model(car_model: str | None, car_model_ids: dict[str, int] | None = None) -> int:
    raw = str(car_model or "").strip()
    try:
        return int(raw)
    except ValueError:
        normalized = "".join(char for char in raw.lower() if char.isalnum())
        configured_ids = DEFAULT_ACC_CAR_MODEL_IDS if car_model_ids is None else car_model_ids
        for configured_name, model_id in configured_ids.items():
            configured_normalized = "".join(char for char in str(configured_name).lower() if char.isalnum())
            if configured_normalized == normalized:
                return int(model_id)
        return ACC_CAR_MODEL_IDS.get(normalized, -1)


def acc_entrylist_entry(
    registration: RaceRegistration,
    user: User,
    car_model: str | None = None,
    car_model_ids: dict[str, int] | None = None,
    driver_category: int = 0,
) -> dict:
    resolved_car_model = (car_model or registration.car_model or "").strip()
    resolved_car_model_id = acc_forced_car_model(resolved_car_model, car_model_ids)
    return {
        "drivers": [
            {
                "firstName": user.first_name,
                "lastName": user.last_name,
                "nickName": user.nickname,
                "shortName": short_driver_name(user, registration.pilot_number),
                "nationality": 0,
                "driverCategory": driver_category,
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
        "carModel": resolved_car_model_id,
        "raceNumber": registration.pilot_number,
        "defaultGridPosition": -1,
        "forcedCarModel": resolved_car_model_id,
        "overrideDriverInfo": 1,
        "isServerAdmin": 0,
        "overrideCarModelForCustomCar": 1,
        "configVersion": 1,
    }


def acc_team_entrylist_entry(
    registration: TeamRaceRegistration,
    team: Team,
    drivers: list[dict],
    car_model_ids: dict[str, int] | None = None,
    driver_categories: list[int] | None = None,
) -> dict:
    resolved_car_model = (registration.car_model or "").strip()
    resolved_car_model_id = acc_forced_car_model(resolved_car_model, car_model_ids)
    return {
        "teamName": f"{team.name} - {team.abbreviation}",
        "raceNumber": registration.race_number,
        "defaultGridPosition": -1,
        "ballastKg": 0,
        "restrictor": 0,
        "isServerAdmin": 0,
        "forcedCarModel": resolved_car_model_id,
        "overrideCarModelForCustomCar": 0,
        "overrideDriverInfo": 1,
        "customCar": "",
        "drivers": [
            {
                "driverCategory": (driver_categories or [0] * len(drivers))[index],
                "firstName": driver.get("first_name"),
                "lastName": driver.get("last_name"),
                "playerID": acc_player_id(driver.get("steam_id")),
                "shortName": driver.get("short_name") or short_driver_name_from_text(driver.get("nickname") or driver.get("login"), registration.race_number),
                "nationality": 0,
            }
            for index, driver in enumerate(drivers)
        ],
    }


def short_driver_name_from_text(value: str | None, fallback_number: int | None = None) -> str:
    letters = "".join(char for char in str(value or "").upper() if char.isalnum())
    return (letters[:3] or f"P{fallback_number or 0}")[:3]


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


async def get_team_registration_rows(session: AsyncSession, race_id: int) -> list[tuple[TeamRaceRegistration, Team]]:
    return list(
        (
            await session.execute(
                select(TeamRaceRegistration, Team)
                .join(Team, Team.id == TeamRaceRegistration.team_id)
                .where(TeamRaceRegistration.race_id == race_id)
                .order_by(TeamRaceRegistration.registered_at, TeamRaceRegistration.id)
            )
        ).all()
    )


async def build_acc_entrylist(session: AsyncSession, race_id: int) -> dict:
    race = await session.get(Race, race_id)
    race_assets = await get_race_assets(session)
    car_model_ids = race_assets.car_model_ids
    game = race.game if race else "ACC"
    license_tiers = (await get_license_settings_value(session)).tiers
    if race and race.is_team_event:
        rows = await get_team_registration_rows(session, race_id)
        return {
            "entries": [
                acc_team_entrylist_entry(
                    registration,
                    team,
                    registration.drivers or [],
                    car_model_ids,
                    [acc_driver_category_for_user(driver, game, license_tiers) for driver in registration.drivers or []],
                )
                for registration, team in rows
            ],
            "forceEntryList": 1,
        }
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
        "entries": [
            acc_entrylist_entry(
                registration,
                user,
                resolved_car(registration, user),
                car_model_ids,
                acc_driver_category_for_user(user, game, license_tiers),
            )
            for registration, user in rows
        ],
        "configVersion": 1,
        "forceEntryList": 1,
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


def acc_line_car_model(line: dict) -> int | str | None:
    car = line.get("car") if isinstance(line.get("car"), dict) else {}
    value = car.get("carModel")
    if value is None:
        value = line.get("carModel", line.get("forcedCarModel"))
    if isinstance(value, str):
        value = value.strip()
        return int(value) if value.isdigit() else value or None
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def normalize_lmu_driver_name(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def lmu_user_keys(user: User) -> set[str]:
    return {
        key
        for key in (
            normalize_lmu_driver_name(user.nickname),
            normalize_lmu_driver_name(user.login),
            normalize_lmu_driver_name(f"{user.first_name} {user.last_name}"),
        )
        if key
    }


async def lmu_user_lookup(session: AsyncSession) -> dict[str, tuple[User, str | None, str | None] | None]:
    rows = list(
        (
            await session.execute(
                select(User, Team.name, Team.abbreviation).outerjoin(Team, Team.id == User.team_id)
            )
        ).all()
    )
    lookup: dict[str, tuple[User, str | None, str | None] | None] = {}
    for user, team_name, team_abbreviation in rows:
        for key in lmu_user_keys(user):
            lookup[key] = (user, team_name, team_abbreviation) if key not in lookup else None
    return lookup


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


def team_driver_lookup_maps(rows: list[tuple[TeamRaceRegistration, Team]]) -> tuple[dict[str, dict], dict[int, TeamRaceRegistration]]:
    by_steam: dict[str, dict] = {}
    by_number: dict[int, TeamRaceRegistration] = {}
    for registration, team in rows:
        by_number[registration.race_number] = registration
        for driver in registration.drivers or []:
            normalized = normalize_acc_player_id(driver.get("steam_id"))
            if normalized:
                by_steam[normalized] = {**driver, "team_id": team.id, "team_name": team.name, "team_abbreviation": team.abbreviation}
    return by_steam, by_number


def acc_line_team_driver(line: dict, drivers_by_steam: dict[str, dict]) -> dict | None:
    player_id = acc_line_player_id(line)
    return drivers_by_steam.get(player_id) if player_id else None


def ensure_acc_team_lines_are_registered(session_name: str, payload: dict, drivers_by_steam: dict[str, dict], teams_by_number: dict[int, TeamRaceRegistration]) -> None:
    missing: list[str] = []
    for position, line in enumerate(payload["sessionResult"]["leaderBoardLines"], start=1):
        driver = acc_line_team_driver(line, drivers_by_steam)
        race_number = acc_line_race_number(line)
        if driver is None and (race_number is None or race_number not in teams_by_number):
            missing.append(acc_line_label(line, position))
    if missing:
        preview = "; ".join(missing[:8])
        suffix = f"; +{len(missing) - 8} more" if len(missing) > 8 else ""
        raise HTTPException(status_code=400, detail=f"ACC {session_name} JSON contains teams or drivers who are not registered for this race: {preview}{suffix}")


async def build_lmu_results_payload(session: AsyncSession, race: Race, qualification_results: dict | None, race_results: dict) -> dict:
    if qualification_results is not None:
        validate_acc_session(qualification_results, "Q")
    validate_acc_session(race_results, "R")
    users_by_name = await lmu_user_lookup(session)
    qualification_by_player = acc_best_lap_map(qualification_results)

    rows: list[dict] = []
    for raw_position, line in enumerate(race_results["sessionResult"]["leaderBoardLines"], start=1):
        driver_name = acc_line_name(line)
        user_match = users_by_name.get(normalize_lmu_driver_name(driver_name))
        user = user_match[0] if user_match else None
        team_name = user_match[1] if user_match else None
        team_abbreviation = user_match[2] if user_match else None
        timing = line.get("timing") or {}
        player_id = acc_line_player_id(line)
        race_number = acc_line_race_number(line)
        finish_ms = timing.get("totalTime")
        driver_total_times = line.get("driverTotalTimes") if isinstance(line.get("driverTotalTimes"), list) else []
        qualification = qualification_by_player.get(player_id, {})
        rows.append(
            {
                "user_id": user.id if user else None,
                "login": user.login if user else None,
                "nickname": user.nickname if user else None,
                "first_name": user.first_name if user else "",
                "last_name": user.last_name if user else "",
                "pilot_number": user.pilot_number if user else None,
                "avatar_color": user.avatar_color if user else "#2563eb",
                "avatar_url": user.avatar_url if user else None,
                "team_id": user.team_id if user else None,
                "team_name": team_name,
                "team_abbreviation": team_abbreviation,
                "rating": int(round(float(user.rating))) if user else None,
                "game_ratings": user.game_ratings if user else {},
                "sr": float(user.sr) if user else None,
                "driver_name": driver_name,
                "match_status": "matched" if user else "unmatched",
                "player_id": acc_player_id(player_id),
                "race_number": race_number,
                "car_model": acc_line_car_model(line),
                "finish_ms": int(finish_ms) if isinstance(finish_ms, (int, float)) else None,
                "driver_total_time_ms": int(driver_total_times[0]) if driver_total_times else None,
                "lap_count": int(timing.get("lapCount") or 0),
                "best_lap_ms": timing.get("bestLap"),
                "qualification_position": qualification.get("qualification_position"),
                "qualification_best_lap_ms": qualification.get("qualification_best_lap_ms"),
                "raw_position": raw_position,
                "source": "lmu",
            }
        )

    return {
        "format": "lmu",
        "track": race_results.get("trackName") or race.track,
        "qualification_enabled": qualification_results is not None,
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
        "rows": rows,
    }


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
            "team_id": user.team_id if user else None,
            "car_model": acc_line_car_model(line),
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
                    "team_id": user.team_id,
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


def build_acc_team_results_payload(race: Race, qualification_results: dict | None, race_results: dict, rows: list[tuple[TeamRaceRegistration, Team]]) -> dict:
    if race.has_qualification and qualification_results is None:
        raise HTTPException(status_code=400, detail="Qualification results JSON is required for this race")
    if qualification_results is not None:
        validate_acc_session(qualification_results, "Q")
    validate_acc_session(race_results, "R")
    drivers_by_steam, teams_by_number = team_driver_lookup_maps(rows)
    if qualification_results is not None:
        ensure_acc_team_lines_are_registered("qualification", qualification_results, drivers_by_steam, teams_by_number)
    ensure_acc_team_lines_are_registered("race", race_results, drivers_by_steam, teams_by_number)
    qualification_by_player = acc_best_lap_map(qualification_results)

    result_rows: list[dict] = []
    matched_team_ids: set[int] = set()
    for raw_position, line in enumerate(race_results["sessionResult"]["leaderBoardLines"], start=1):
        player_id = acc_line_player_id(line)
        race_number = acc_line_race_number(line)
        team_registration = teams_by_number.get(race_number) if race_number is not None else None
        driver = acc_line_team_driver(line, drivers_by_steam)
        if team_registration is None and driver is not None:
            team_registration = next((registration for registration, team in rows if team.id == driver.get("team_id")), None)
        team = next((team for registration, team in rows if registration.id == getattr(team_registration, "id", None)), None)
        timing = line.get("timing") or {}
        finish_ms = timing.get("totalTime")
        driver_total_times = line.get("driverTotalTimes") if isinstance(line.get("driverTotalTimes"), list) else []
        qualification = qualification_by_player.get(player_id, {})
        if team_registration is not None:
            matched_team_ids.add(team_registration.team_id)
        result_rows.append(
            {
                "user_id": driver.get("user_id") if driver else None,
                "login": driver.get("login") if driver else None,
                "nickname": driver.get("nickname") if driver else None,
                "first_name": driver.get("first_name") if driver else "",
                "last_name": driver.get("last_name") if driver else "",
                "pilot_number": driver.get("pilot_number") if driver else None,
                "driver_name": acc_line_name(line),
                "player_id": acc_player_id(player_id),
                "race_number": race_number if race_number is not None else (team_registration.race_number if team_registration else None),
                "team_id": team_registration.team_id if team_registration else driver.get("team_id") if driver else None,
                "team_name": team.name if team else driver.get("team_name") if driver else None,
                "team_abbreviation": team.abbreviation if team else driver.get("team_abbreviation") if driver else None,
                "car_model": acc_line_car_model(line),
                "finish_ms": int(finish_ms) if isinstance(finish_ms, (int, float)) else None,
                "driver_total_time_ms": int(driver_total_times[0]) if driver_total_times else None,
                "lap_count": int(timing.get("lapCount") or 0),
                "best_lap_ms": timing.get("bestLap"),
                "qualification_position": qualification.get("qualification_position"),
                "qualification_best_lap_ms": qualification.get("qualification_best_lap_ms"),
                "raw_position": raw_position,
                "source": "acc_team",
            }
        )

    for registration, team in rows:
        if team.id not in matched_team_ids:
            lead_driver = next(iter(registration.drivers or []), {})
            result_rows.append(
                {
                    "user_id": lead_driver.get("user_id"),
                    "login": lead_driver.get("login"),
                    "nickname": lead_driver.get("nickname"),
                    "driver_name": lead_driver.get("nickname") or lead_driver.get("login") or team.name,
                    "player_id": acc_player_id(lead_driver.get("steam_id")),
                    "race_number": registration.race_number,
                    "team_id": team.id,
                    "team_name": team.name,
                    "team_abbreviation": team.abbreviation,
                    "car_model": registration.car_model,
                    "finish_ms": None,
                    "lap_count": 0,
                    "best_lap_ms": None,
                    "qualification_position": None,
                    "qualification_best_lap_ms": None,
                    "raw_position": None,
                    "source": "acc_team",
                    "status": "missing",
                }
            )

    return {
        "format": "acc_team",
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


def manual_result_pilot_data(user: User, team_name: str | None = None, team_abbreviation: str | None = None) -> dict:
    return {
        "user_id": user.id,
        "login": user.login,
        "nickname": user.nickname,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "pilot_number": user.pilot_number,
        "race_number": user.pilot_number,
        "avatar_color": user.avatar_color,
        "avatar_url": user.avatar_url,
        "team_id": user.team_id,
        "team_name": team_name,
        "team_abbreviation": team_abbreviation,
        "rating": int(round(float(user.rating))),
        "game_ratings": user.game_ratings or {},
        "sr": float(user.sr),
        "country": user.country,
        "driver_name": " ".join(filter(None, [user.first_name, user.last_name])) or user.nickname or user.login,
    }


async def get_manual_result_pilots(session: AsyncSession, user_ids: set[int]) -> dict[int, dict]:
    if not user_ids:
        return {}
    rows = (
        await session.execute(
            select(User, Team.name, Team.abbreviation)
            .outerjoin(Team, Team.id == User.team_id)
            .where(User.id.in_(user_ids))
        )
    ).all()
    return {user.id: manual_result_pilot_data(user, team_name, team_abbreviation) for user, team_name, team_abbreviation in rows}


def build_manual_results_payload(race: Race, payload: ManualResultsUpload, registered: list[dict], manual_pilots: dict[int, dict] | None = None) -> dict:
    registered_by_id = {int(item["user_id"]): item for item in registered if item.get("user_id") is not None}
    pilots_by_id = manual_pilots if race.game == "LMU" else registered_by_id
    qualification_by_user: dict[int, dict] = {}
    if race.game == "ACC":
        qualification_values = [
            (index, row.user_id, row.qualification_best_lap_ms)
            for index, row in enumerate(payload.rows)
            if row.qualification_best_lap_ms is not None
        ]
        if race.has_qualification and not qualification_values:
            raise HTTPException(status_code=400, detail="Qualification results are required for this race")
        for position, (_, user_id, best_lap_ms) in enumerate(sorted(qualification_values, key=lambda item: (item[2], item[0])), start=1):
            qualification_by_user[user_id] = {"position": position, "best_lap_ms": best_lap_ms}
    rows: list[dict] = []
    seen: set[int] = set()
    for row in payload.rows:
        if row.user_id in seen:
            raise HTTPException(status_code=400, detail=f"Duplicate pilot in results: {row.user_id}")
        if row.user_id not in pilots_by_id:
            detail = "Pilot is not found" if race.game == "LMU" else "Pilot is not registered for this race"
            raise HTTPException(status_code=400, detail=f"{detail}: {row.user_id}")
        pilot = pilots_by_id[row.user_id]
        qualification = qualification_by_user.get(row.user_id, {})
        seen.add(row.user_id)
        rows.append(
            {
                "user_id": row.user_id,
                "login": pilot.get("login"),
                "nickname": pilot.get("nickname"),
                "first_name": pilot.get("first_name") or "",
                "last_name": pilot.get("last_name") or "",
                "pilot_number": pilot.get("pilot_number"),
                "race_number": pilot.get("race_number") or pilot.get("pilot_number"),
                "car_model": acc_line_car_model({"carModel": pilot.get("car_model")}) if race.game == "ACC" else pilot.get("car_model"),
                "avatar_color": pilot.get("avatar_color") or "#2563eb",
                "avatar_url": pilot.get("avatar_url"),
                "team_id": pilot.get("team_id"),
                "team_name": pilot.get("team_name"),
                "team_abbreviation": pilot.get("team_abbreviation"),
                "rating": pilot.get("rating"),
                "game_ratings": pilot.get("game_ratings") or {},
                "sr": pilot.get("sr"),
                "country": pilot.get("country"),
                "driver_name": " ".join(filter(None, [pilot.get("first_name"), pilot.get("last_name")])) or pilot.get("nickname"),
                "finish_ms": row.finish_ms,
                "lap_count": row.lap_count,
                "best_lap_ms": row.best_lap_ms,
                "qualification_position": qualification.get("position"),
                "qualification_best_lap_ms": qualification.get("best_lap_ms"),
                "source": "lmu_manual" if race.game == "LMU" else ("acc_manual" if race.game == "ACC" else "manual"),
            }
        )
    if race.game == "LMU":
        return {"format": "lmu_manual", "track": race.track, "qualification_enabled": False, "rows": rows}
    for user_id, pilot in registered_by_id.items():
        if user_id not in seen:
            rows.append(
                {
                    "user_id": user_id,
                    "login": pilot.get("login"),
                    "nickname": pilot.get("nickname"),
                    "first_name": pilot.get("first_name") or "",
                    "last_name": pilot.get("last_name") or "",
                    "pilot_number": pilot.get("pilot_number"),
                    "race_number": pilot.get("pilot_number"),
                    "car_model": acc_line_car_model({"carModel": pilot.get("car_model")}) if race.game == "ACC" else pilot.get("car_model"),
                    "avatar_color": pilot.get("avatar_color") or "#2563eb",
                    "avatar_url": pilot.get("avatar_url"),
                    "team_id": pilot.get("team_id"),
                    "team_name": pilot.get("team_name"),
                    "team_abbreviation": pilot.get("team_abbreviation"),
                    "rating": pilot.get("rating"),
                    "game_ratings": pilot.get("game_ratings") or {},
                    "sr": pilot.get("sr"),
                    "country": pilot.get("country"),
                    "driver_name": " ".join(filter(None, [pilot.get("first_name"), pilot.get("last_name")])) or pilot.get("nickname"),
                    "finish_ms": None,
                    "lap_count": 0,
                    "best_lap_ms": None,
                    "qualification_position": None,
                    "qualification_best_lap_ms": None,
                    "source": "acc_manual" if race.game == "ACC" else "manual",
                    "status": "missing",
                }
            )
    if race.game == "ACC":
        return {
            "format": "acc_manual",
            "track": race.track,
            "qualification_enabled": race.has_qualification,
            "qualification": {"session_type": "Q", "manual": True} if race.has_qualification else None,
            "race": {"session_type": "R", "manual": True},
            "rows": rows,
        }
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


async def ensure_team_race_number_available(session: AsyncSession, race_id: int, race_number: int, exclude_registration_id: int | None = None) -> None:
    stmt = select(TeamRaceRegistration.id).where(
        TeamRaceRegistration.race_id == race_id,
        TeamRaceRegistration.race_number == race_number,
    )
    if exclude_registration_id is not None:
        stmt = stmt.where(TeamRaceRegistration.id != exclude_registration_id)
    if await session.scalar(stmt):
        raise HTTPException(status_code=409, detail="Race number is already taken in this race")


async def build_team_driver_payloads(session: AsyncSession, team: Team, driver_ids: list[int]) -> list[dict]:
    rows = (
        await session.scalars(
            select(User)
            .where(User.id.in_(driver_ids), User.team_id == team.id, User.status == UserStatus.active)
        )
    ).all()
    users_by_id = {user.id: user for user in rows}
    missing = [user_id for user_id in driver_ids if user_id not in users_by_id]
    if missing:
        raise HTTPException(status_code=400, detail=f"Drivers must be active members of your team: {', '.join(map(str, missing))}")
    return [
        {
            "user_id": user.id,
            "login": user.login,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "nickname": user.nickname,
            "pilot_number": user.pilot_number,
            "steam_id": user.steam_id,
            "country": user.country,
            "short_name": short_driver_name(user, user.pilot_number),
            "avatar_color": user.avatar_color,
            "avatar_url": user.avatar_url,
            "rating": int(round(float(user.rating))),
            "game_ratings": user.game_ratings or {},
            "sr": float(user.sr),
        }
        for user in (users_by_id[user_id] for user_id in driver_ids)
    ]


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

    team_rows = (
        await session.execute(
            select(TeamRaceRegistration)
            .options(selectinload(TeamRaceRegistration.team))
            .where(TeamRaceRegistration.race_id.in_(race_ids))
            .order_by(TeamRaceRegistration.race_id, TeamRaceRegistration.registered_at, TeamRaceRegistration.id)
        )
    ).scalars().all()
    grouped_team_rows: dict[int, list[TeamRaceRegistration]] = {race_id: [] for race_id in race_ids}
    for registration in team_rows:
        grouped_team_rows.setdefault(registration.race_id, []).append(registration)
    for race in races:
        set_committed_value(race, "team_registrations", grouped_team_rows.get(race.id, []))


@router.get("", response_model=list[RaceRead])
@limiter.limit("1200/minute")
async def list_races(
    request: Request,
    status_filter: str = "all",
    game_filter: str = "all",
    has_qualification: bool | None = None,
    is_team_event: bool | None = None,
    is_official: bool | None = None,
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
    if has_qualification is not None:
        stmt = stmt.where(Race.has_qualification == has_qualification)
    if is_team_event is not None:
        stmt = stmt.where(Race.is_team_event == is_team_event)
    if is_official is not None:
        stmt = stmt.where(Race.is_official == is_official)
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
    has_qualification: bool | None = None,
    is_team_event: bool | None = None,
    is_official: bool | None = None,
    search: str | None = None,
    offset: int = 0,
    limit: int = 500,
    _: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    limit = min(limit, 1000)
    solo_registered_count = (
        select(func.count(RaceRegistration.id))
        .where(RaceRegistration.race_id == Race.id)
        .correlate(Race)
        .scalar_subquery()
        .label("registered_count")
    )
    team_registered_count = (
        select(func.count(TeamRaceRegistration.id))
        .where(TeamRaceRegistration.race_id == Race.id)
        .correlate(Race)
        .scalar_subquery()
        .label("team_registered_count")
    )
    stmt = (
        select(Race, solo_registered_count, team_registered_count)
    )
    if status_filter == "not_finished":
        stmt = stmt.where(Race.status != RaceStatus.finished)
    elif status_filter in RaceStatus._value2member_map_:
        stmt = stmt.where(Race.status == RaceStatus(status_filter))
    if game_filter in RACE_GAMES:
        stmt = stmt.where(Race.game == game_filter)
    if has_qualification is not None:
        stmt = stmt.where(Race.has_qualification == has_qualification)
    if is_team_event is not None:
        stmt = stmt.where(Race.is_team_event == is_team_event)
    if is_official is not None:
        stmt = stmt.where(Race.is_official == is_official)
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
    for race, _, _ in rows:
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
            "lmu_results_at": race.lmu_results_at,
            "status": race.status,
            "registration_start": race.registration_start,
            "datetime_start": race.datetime_start,
            "datetime_end": race.datetime_end,
            "max_pilots": race.max_pilots,
            "registered_count": int((team_count if race.is_team_event else count) or 0),
            "car_class": race.car_class,
            "track": race.track,
            "track_id": race.track_id,
            "weather_chances": race.weather_chances or {},
            "track_temperature": race.track_temperature,
            "game": race.game,
            "has_qualification": race.has_qualification,
            "scoring_system": race.scoring_system,
            "pole_bonus_enabled": race.pole_bonus_enabled,
            "is_team_event": race.is_team_event,
            "rating_applied": race.rating_applied,
            "championship_id": race.championship_id,
            "championship_round": race.championship_round,
            "creator_id": race.creator_id,
            "is_official": race.is_official,
            "created_at": race.created_at,
            "updated_at": race.updated_at,
        }
        for race, count, team_count in rows
    ]


@router.post("", response_model=RaceRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def create_race(payload: RaceCreate, request: Request, user: User = Depends(require_moder_plus), session: AsyncSession = Depends(get_session)):
    if not (payload.registration_start < payload.datetime_end < payload.datetime_start):
        raise HTTPException(status_code=400, detail="Registration dates must end before the race date")
    data = await normalize_race_create_assets(session, payload.model_dump())
    data = normalize_external_race_data(data)
    race = Race(
        **data,
        creator_id=user.id,
        status=RaceStatus.not_started,
        is_passed=False,
        registered_pilots=[],
    )
    update_time_based_status(race)
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


def race_average_lap_ms(results: dict | list | None) -> int | None:
    samples: list[float] = []
    for row in result_rows(results):
        if row.get("status") == "missing":
            continue
        finish_ms = next(
            (
                float(row.get(field))
                for field in ("adjusted_finish_ms", "finish_ms", "driver_total_time_ms")
                if isinstance(row.get(field), (int, float)) and float(row.get(field)) > 0
            ),
            None,
        )
        laps = next(
            (
                float(row.get(field))
                for field in ("lap_count", "laps")
                if isinstance(row.get(field), (int, float)) and float(row.get(field)) > 0
            ),
            0,
        )
        best_lap_ms = next(
            (
                float(row.get(field))
                for field in ("best_lap_ms", "qualification_best_lap_ms")
                if isinstance(row.get(field), (int, float)) and float(row.get(field)) > 0
            ),
            None,
        )
        average_lap = finish_ms / laps if finish_ms is not None and laps else best_lap_ms
        if average_lap is not None and average_lap > 0:
            samples.append(average_lap)
    return round(sum(samples) / len(samples)) if samples else None


@router.get("/track-stats")
@limiter.limit("600/minute")
async def get_track_stats(
    request: Request,
    game: str = "ACC",
    track: str | None = None,
    track_id: str | None = None,
    _: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    if game not in RACE_GAMES:
        raise HTTPException(status_code=400, detail="Unknown simulator")
    normalized_track = str(track or "").strip().casefold()
    normalized_track_id = str(track_id or "").strip()
    if not normalized_track and not normalized_track_id:
        raise HTTPException(status_code=400, detail="Track is required")

    races = list(
        (
            await session.scalars(
                select(Race)
                .where(Race.status == RaceStatus.finished, Race.game == game, Race.results.is_not(None))
                .order_by(Race.datetime_start.desc(), Race.id.desc())
                .limit(1000)
            )
        ).all()
    )
    samples: list[int] = []
    race_count = 0
    for race in races:
        result_track = race.results.get("track") if isinstance(race.results, dict) else None
        names = {str(value).strip().casefold() for value in (race.track, result_track) if value}
        matches_id = bool(normalized_track_id and race.track_id == normalized_track_id)
        matches_name = bool(normalized_track and normalized_track in names)
        if not (matches_id or matches_name):
            continue
        average_lap = race_average_lap_ms(race.results)
        if average_lap is None:
            continue
        race_count += 1
        samples.append(average_lap)

    return {
        "game": game,
        "track": track,
        "track_id": track_id,
        "average_lap_ms": round(sum(samples) / len(samples)) if samples else None,
        "race_count": race_count,
        "sample_count": len(samples),
    }


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
    schedule_changed = any(field in data for field in ("registration_start", "datetime_start", "datetime_end"))
    if schedule_changed and race.championship_id is None:
        registration_start = data.get("registration_start", race.registration_start)
        registration_end = data.get("datetime_end", race.datetime_end)
        race_time = data.get("datetime_start", race.datetime_start)
        if not (registration_start < registration_end < race_time):
            raise HTTPException(status_code=400, detail="Registration dates must end before the race date")
    if requested_status == RaceStatus.finished:
        finish_game = data.get("game", race.game)
        finish_lmu_results_at = data.get("lmu_results_at", race.lmu_results_at)
        if finish_game == "LMU" and finish_lmu_results_at and to_utc(finish_lmu_results_at) > datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="LMU race can be finished after the configured finish time")
    if requested_status == RaceStatus.finished and requested_results is None and race.results is None:
        raise HTTPException(status_code=400, detail="Upload race results before finishing the race")
    data = await normalize_race_update_assets(session, race, data)
    data = normalize_external_race_data(data, race)
    if was_finished and (requested_results is not None or not will_be_finished):
        await restore_race_sr_bonus(session, race)
    for field, value in data.items():
        setattr(race, field, value)
    if schedule_changed and requested_status is None:
        update_time_based_status(race)
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
    if race.is_team_event:
        raise HTTPException(status_code=400, detail="Use team registration for this race")
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

    if registration_number == 0:
        raise HTTPException(status_code=400, detail="Pilot number 000 is not allowed")
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


@router.post("/{race_id}/team-register", response_model=RaceRead)
@limiter.limit("120/minute")
async def register_team_for_race(
    race_id: int,
    request: Request,
    payload: TeamRaceRegisterRequest,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Race).where(Race.id == race_id).with_for_update())
    race = result.scalar_one_or_none()
    if race is None:
        raise HTTPException(status_code=404, detail="Race not found")
    update_time_based_status(race)
    if not race.is_team_event:
        raise HTTPException(status_code=400, detail="This race uses pilot registration")
    if race.championship_id is not None:
        if race.status != RaceStatus.not_started:
            raise HTTPException(status_code=400, detail="Championship stage registration is closed")
    elif race.status != RaceStatus.registration_open:
        raise HTTPException(status_code=400, detail="Registration is not open")
    if payload.race_number == 0:
        raise HTTPException(status_code=400, detail="Race number 000 is not allowed")
    if user.team_id is None:
        raise HTTPException(status_code=403, detail="Create or join a team first")
    team = await session.get(Team, user.team_id)
    if team is None or team.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the team owner can register the team")
    car_model = payload.car_model.strip()
    if race.allowed_cars and car_model not in race.allowed_cars:
        raise HTTPException(status_code=400, detail="Car is not allowed")
    driver_ids = [driver.user_id for driver in payload.drivers]
    drivers = await build_team_driver_payloads(session, team, driver_ids)
    existing = await session.scalar(
        select(TeamRaceRegistration).where(
            TeamRaceRegistration.race_id == race.id,
            TeamRaceRegistration.team_id == team.id,
        )
    )
    await ensure_team_race_number_available(session, race.id, payload.race_number, existing.id if existing else None)
    if existing is None:
        registered_count = await session.scalar(select(func.count()).select_from(TeamRaceRegistration).where(TeamRaceRegistration.race_id == race.id))
        if (registered_count or 0) >= race.max_pilots:
            raise HTTPException(status_code=409, detail="Race is full")
        session.add(
            TeamRaceRegistration(
                race_id=race.id,
                team_id=team.id,
                car_model=car_model,
                race_number=payload.race_number,
                drivers=drivers,
                registered_by=user.id,
                registered_at=datetime.now(timezone.utc),
            )
        )
    else:
        existing.car_model = car_model
        existing.race_number = payload.race_number
        existing.drivers = drivers
        existing.registered_by = user.id
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Team or race number is already registered") from exc
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
    if race.is_team_event:
        raise HTTPException(status_code=400, detail="Use team registration for this race")
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


@router.delete("/{race_id}/registrations/{user_id}", response_model=RaceRead)
@limiter.limit("120/minute")
async def remove_pilot_registration(
    race_id: int,
    user_id: int,
    request: Request,
    _: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Race).where(Race.id == race_id).with_for_update())
    race = result.scalar_one_or_none()
    if race is None:
        raise HTTPException(status_code=404, detail="Race not found")
    update_time_based_status(race)
    if race.is_team_event:
        raise HTTPException(status_code=400, detail="Team registrations are removed by team")
    if race.status in {RaceStatus.ongoing, RaceStatus.finished}:
        raise HTTPException(status_code=400, detail="Registration can be changed only before the race starts")
    registration = await session.scalar(
        select(RaceRegistration).where(
            RaceRegistration.race_id == race.id,
            RaceRegistration.user_id == user_id,
        )
    )
    if registration is not None:
        await session.delete(registration)
        await session.commit()
    await session.refresh(race)
    await attach_registered_pilots(session, [race])
    return race


@router.delete("/{race_id}/team-register", response_model=RaceRead)
@limiter.limit("120/minute")
async def unregister_team_from_race(
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
    if not race.is_team_event:
        raise HTTPException(status_code=400, detail="This race uses pilot registration")
    if race.championship_id is not None:
        if race.status != RaceStatus.not_started:
            raise HTTPException(status_code=400, detail="Championship stage registration is closed")
    elif race.status != RaceStatus.registration_open:
        raise HTTPException(status_code=400, detail="Registration is not open")
    if user.team_id is None:
        raise HTTPException(status_code=403, detail="Create or join a team first")
    team = await session.get(Team, user.team_id)
    if team is None or team.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the team owner can unregister the team")
    registration = await session.scalar(
        select(TeamRaceRegistration).where(
            TeamRaceRegistration.race_id == race.id,
            TeamRaceRegistration.team_id == team.id,
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
    if race.is_team_event:
        rows = await get_team_registration_rows(session, race.id)
        return {"race_id": race.id, "team_registrations": [team_registration_to_json(registration, team) for registration, team in rows]}
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
        raise HTTPException(status_code=400, detail="Use simulator JSON upload for ACC races")
    if race.game == "LMU":
        raise HTTPException(status_code=400, detail="Use manual result upload for LMU races")
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
    ensure_can_manage_race(user, race, "upload simulator results to")
    if race.game != "ACC":
        raise HTTPException(status_code=400, detail="Simulator result JSON can only be uploaded for ACC races")
    registration_rows = await get_registration_rows(session, race.id)
    team_registration_rows = await get_team_registration_rows(session, race.id) if race.is_team_event else []
    if race.status == RaceStatus.finished:
        await restore_race_sr_bonus(session, race)
    race.results = (
        build_acc_team_results_payload(race, payload.qualification_results, payload.race_results, team_registration_rows)
        if race.is_team_event
        else build_acc_results_payload(race, payload.qualification_results, payload.race_results, registration_rows)
    )
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
    registered = await get_registered_pilots(session, race.id)
    manual_pilots = await get_manual_result_pilots(session, {row.user_id for row in payload.rows}) if race.game == "LMU" else None
    if race.status == RaceStatus.finished:
        await restore_race_sr_bonus(session, race)
    race.results = build_manual_results_payload(race, payload, registered, manual_pilots)
    race.status = RaceStatus.finished
    race.is_passed = True
    await recalculate_race_results(session, race)
    await apply_sr_penalties(session, race)
    await recalculate_all_ratings(session)
    await session.commit()
    await session.refresh(race)
    await attach_registered_pilots(session, [race])
    return race
