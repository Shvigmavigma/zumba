import asyncio
import json
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select, update

from app.avatar_uploads import remove_avatar_file
from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    AppSetting,
    Appeal,
    AppealStatus,
    Championship,
    ChampionshipRegistration,
    ChampionshipScoringSystem,
    DEFAULT_RATING,
    DEFAULT_SR,
    MAX_SR,
    Penalty,
    PenaltyStatus,
    PenaltyType,
    Race,
    RaceFanVote,
    RaceRegistration,
    RaceStatus,
    Role,
    Setup,
    Team,
    TeamApplication,
    TeamApplicationStatus,
    TeamCreationRequest,
    User,
    UserStatus,
)
from app.race_assets import assets_for_game, get_race_assets, save_race_assets
from app.race_videos import remove_race_video_file
from app.schemas import RaceAssetsConfig
from app.security import hash_password
from app.services import apply_sr_penalties, recalculate_all_ratings, recalculate_race_results


SIM_PASSWORD = "BmrlYear2026!"
SIM_USER_COUNT = 200
SIM_TEAM_COUNT = 40
SIM_CHAMPIONSHIP_COUNT = 10
RACES_PER_GAME = 300
OPEN_REGISTRATION_RACE_COUNT = 10
ONGOING_RACE_COUNT = 5
TEAM_MEMBER_LIMIT = 12
RANDOM_SEED = 14082026

GAMES = ["ACC", "AC", "iRacing", "LMU"]
COLORS = ["#1652D8", "#0D2F8F", "#2563eb", "#0891b2", "#16a34a", "#9333ea", "#dc2626", "#f97316"]
COUNTRIES = [
    "Germany",
    "Italy",
    "Spain",
    "France",
    "Poland",
    "Brazil",
    "Japan",
    "United States",
    "United Kingdom",
    "Finland",
    "Sweden",
    "Norway",
    "Netherlands",
    "Belgium",
    "Portugal",
    "Canada",
    "Australia",
    "Argentina",
    "Austria",
    "Czechia",
    "Ukraine",
]
TEAM_NAMES = [
    "BMRL Factory",
    "Apex Line",
    "Curb Hunters",
    "Sector Ghosts",
    "Redline Union",
    "Kerb Syndicate",
    "Slipstream Works",
    "Night Stint",
    "Delta Racing",
    "Vortex Garage",
    "Prime Apex",
    "Iron Sector",
    "Blue Flag Lab",
    "Overcut Crew",
    "Pit Wall Club",
    "Throttle House",
    "Final Lap",
    "Pole Hunters",
    "Brake Bias",
    "Track Limits",
    "Carbon Wing",
    "Rain Masters",
    "Turbo Draft",
    "Racing Craft",
    "Grid Walk",
    "Full Course",
    "Start Lights",
    "Late Apex",
    "Replay Room",
    "Victory Lane",
    "Understeer Lab",
    "Oversteer Club",
    "Race Control",
    "Endurance Works",
    "Hotlap Project",
    "Blue Sector",
    "Pit Exit",
    "Trackside Union",
    "Night Shift",
    "Aero Balance",
]
FALLBACK_ASSETS = {
    "ACC": {
        "tracks": ["Spa-Francorchamps", "Monza", "Kyalami", "Barcelona", "Silverstone", "Suzuka"],
        "classes": {
            "GT3": ["BMW M4 GT3 2021", "Ferrari 296 GT3 2023", "Porsche 992 GT3R 2023", "McLaren 720S Evo GT3 2023"],
            "GT4": ["BMW M4 2018", "McLaren 570S 2016", "Porsche 718 Cayman GT4 Clubsport 2019"],
        },
    },
    "AC": {
        "tracks": ["Nordschleife", "Red Bull Ring", "Silverstone", "Laguna Seca", "Road America", "Watkins Glen"],
        "classes": {
            "GT3": ["Ferrari 488 GT3", "BMW Z4 GT3", "Mercedes AMG GT3", "Porsche 911 GT3 R"],
            "Cup": ["Mazda MX-5 Cup", "Porsche 911 Cup", "BMW M235i Racing"],
        },
    },
    "iRacing": {
        "tracks": ["Sebring", "Daytona Road", "Road Atlanta", "Fuji Speedway", "Suzuka", "Le Mans"],
        "classes": {
            "GT3": ["Ferrari 296 GT3", "Mercedes-AMG GT3 2020", "BMW M4 GT3", "Porsche 911 GT3 R"],
            "Prototype": ["Dallara P217", "BMW M Hybrid V8", "Cadillac V-Series.R"],
        },
    },
    "LMU": {
        "tracks": ["Le Mans", "Spa-Francorchamps", "Monza", "Fuji", "Sebring", "Bahrain"],
        "classes": {
            "Hypercar": ["Ferrari 499P", "Toyota GR010", "Porsche 963", "Cadillac V-Series.R"],
            "LMGT3": ["BMW M4 LMGT3", "Ferrari 296 LMGT3", "Porsche 911 LMGT3 R"],
        },
    },
}
CHAMPIONSHIP_SPECS = [
    ("BMRL ACC Winter Cup", "ACC", "GT3", 10, ChampionshipScoringSystem.fia, True),
    ("BMRL AC Classic Trophy", "AC", "GT3", 10, ChampionshipScoringSystem.linear, False),
    ("BMRL iRacing Road Series", "iRacing", "GT3", 10, ChampionshipScoringSystem.fia, True),
    ("BMRL LMU Hypercar League", "LMU", "Hypercar", 10, ChampionshipScoringSystem.endurance, False),
    ("BMRL ACC GT4 Sprint", "ACC", "GT4", 10, ChampionshipScoringSystem.fia, False),
    ("BMRL AC Cup Challenge", "AC", "Cup", 10, ChampionshipScoringSystem.linear, True),
    ("BMRL iRacing Prototype Tour", "iRacing", "Prototype", 10, ChampionshipScoringSystem.endurance, False),
    ("BMRL LMU GT Series", "LMU", "LMGT3", 10, ChampionshipScoringSystem.fia, True),
    ("BMRL ACC Endurance Masters", "ACC", "GT3", 10, ChampionshipScoringSystem.endurance, True),
    ("BMRL iRacing Night Cup", "iRacing", "GT3", 10, ChampionshipScoringSystem.fia, False),
]


def role_for_index(index: int) -> Role:
    if index in {1, 2}:
        return Role.moder
    if index in {3, 4}:
        return Role.marshall
    if index in {5, 6}:
        return Role.smm
    return Role.pilot


def status_for_index(index: int) -> UserStatus:
    if index % 97 == 0:
        return UserStatus.banned
    if index % 89 == 0:
        return UserStatus.timeout
    if index % 83 == 0:
        return UserStatus.unapproved
    return UserStatus.active


def user_games(index: int) -> list[str]:
    variants = [
        ["ACC", "AC", "iRacing", "LMU"],
        ["ACC", "AC"],
        ["ACC", "iRacing"],
        ["ACC", "LMU"],
        ["AC", "iRacing"],
        ["AC", "LMU"],
        ["iRacing", "LMU"],
        ["ACC"],
        ["AC"],
        ["iRacing"],
        ["LMU"],
    ]
    return variants[index % len(variants)]


def team_abbreviation(name: str, index: int, used: set[str]) -> str:
    raw = "".join(part[0] for part in name.replace("-", " ").split() if part).upper()
    candidate = (raw + "XXX")[:3]
    if candidate not in used:
        used.add(candidate)
        return candidate
    value = index
    while True:
        candidate = "".join(chr(65 + item) for item in ((value // 676) % 26, (value // 26) % 26, value % 26))
        if candidate not in used:
            used.add(candidate)
            return candidate
        value += 1


def display_name(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip() or user.nickname or user.login


def ms_to_line(row: dict, session_type: str) -> dict:
    player_id = str(row.get("player_id") or "").removeprefix("S")
    return {
        "car": {
            "carModel": row.get("car_model"),
            "raceNumber": row.get("race_number"),
            "drivers": [
                {
                    "firstName": row.get("first_name") or "BMRL",
                    "lastName": row.get("last_name") or "Driver",
                    "shortName": (row.get("nickname") or row.get("login") or "SIM")[:3].upper(),
                    "playerId": f"S{player_id}",
                }
            ],
        },
        "currentDriver": {
            "firstName": row.get("first_name") or "BMRL",
            "lastName": row.get("last_name") or "Driver",
            "shortName": (row.get("nickname") or row.get("login") or "SIM")[:3].upper(),
            "playerId": f"S{player_id}",
        },
        "timing": {
            "bestLap": row.get("best_lap_ms"),
            "totalTime": row.get("finish_ms") if session_type == "R" else row.get("best_lap_ms"),
            "lapCount": row.get("lap_count") or 0,
        },
    }


def assert_no_zero_times(value, path: str = "results") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"finish_ms", "best_lap_ms", "adjusted_finish_ms", "qualification_best_lap_ms", "totalTime", "bestLap"} and item == 0:
                raise ValueError(f"Zero time is not allowed at {path}.{key}")
            assert_no_zero_times(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            assert_no_zero_times(item, f"{path}[{index}]")


async def ensure_sim_race_assets(session, asset_config: RaceAssetsConfig) -> RaceAssetsConfig:
    data = asset_config.model_dump()
    games = data.setdefault("games", {})
    changed = False
    for game in GAMES:
        game_config = dict(games.get(game) or {})
        fallback = FALLBACK_ASSETS[game]
        if not game_config.get("tracks"):
            game_config["tracks"] = list(fallback["tracks"])
            changed = True
        if not game_config.get("classes"):
            game_config["classes"] = [
                {"name": name, "cars": list(cars)}
                for name, cars in fallback["classes"].items()
            ]
            changed = True
        games[game] = game_config
    data["games"] = games
    data.update(games["ACC"])
    return await save_race_assets(session, RaceAssetsConfig.model_validate(data)) if changed else asset_config


def asset_catalog(asset_config) -> dict[str, dict[str, object]]:
    catalog = {}
    for game in GAMES:
        game_config = assets_for_game(asset_config, game)
        tracks = list(game_config.tracks or FALLBACK_ASSETS[game]["tracks"])
        track_ids = {track: game_config.track_ids.get(track, track.lower()) for track in tracks}
        classes = {item.name: list(item.cars) for item in game_config.classes if item.cars}
        if not classes:
            classes = FALLBACK_ASSETS[game]["classes"]
        catalog[game] = {"tracks": tracks, "track_ids": track_ids, "classes": classes}
    return catalog


def catalog_track_id(catalog: dict, game: str, track: str) -> str | None:
    return catalog[game].get("track_ids", {}).get(track)


def class_cars(catalog: dict, game: str, car_class: str) -> list[str]:
    classes = catalog[game]["classes"]
    if car_class in classes:
        return list(classes[car_class])
    first = next(iter(classes.values()))
    return list(first)


def random_class(catalog: dict, game: str) -> str:
    return random.choice(list(catalog[game]["classes"].keys()))


async def ensure_admin(session) -> User:
    settings = get_settings()
    admin = await session.scalar(select(User).where(User.login == settings.admin_login))
    if admin is None:
        admin = User(
            login=settings.admin_login,
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            first_name="System",
            last_name="Admin",
            nickname="Admin",
            pilot_number=1,
            country="Global",
            sr=DEFAULT_SR,
            rating=DEFAULT_RATING,
            rating_race_count=0,
            discord=None,
            steam_id="admin-steam",
            role=Role.admin,
            status=UserStatus.active,
            avatar_color="#1652D8",
            games=GAMES,
        )
        session.add(admin)
        await session.flush()
    admin.role = Role.admin
    admin.status = UserStatus.active
    admin.sr = DEFAULT_SR
    admin.rating = DEFAULT_RATING
    admin.rating_race_count = 0
    admin.ban_end = None
    admin.timeout_start = None
    admin.timeout_end = None
    admin.pending_profile_changes = None
    admin.games = GAMES
    admin.team_id = None
    return admin


async def wipe_data(session, admin: User) -> dict[str, list[str]]:
    files = {"avatars": [], "videos": []}
    files["avatars"].extend([url for url in (await session.scalars(select(User.avatar_url))).all() if url])
    files["avatars"].extend([url for url in (await session.scalars(select(Team.avatar_url))).all() if url])
    files["videos"].extend([url for url in (await session.scalars(select(Race.video_url))).all() if url])

    await session.execute(delete(RaceFanVote))
    await session.execute(delete(Appeal))
    await session.execute(delete(Penalty))
    await session.execute(delete(RaceRegistration))
    await session.execute(delete(ChampionshipRegistration))
    await session.execute(delete(Setup))
    await session.execute(delete(Race))
    await session.execute(delete(Championship))
    await session.execute(delete(TeamApplication))
    await session.execute(delete(TeamCreationRequest))
    await session.execute(update(User).values(team_id=None))
    await session.execute(delete(Team))
    await session.execute(delete(User).where(User.id != admin.id))
    await session.flush()
    return files


async def save_team_limit(session) -> None:
    setting = await session.get(AppSetting, "team_member_limit")
    if setting is None:
        session.add(AppSetting(key="team_member_limit", value={"limit": TEAM_MEMBER_LIMIT}))
    else:
        setting.value = {"limit": TEAM_MEMBER_LIMIT}


async def create_users(session, admin: User, now: datetime) -> list[User]:
    used_numbers = {admin.pilot_number}
    available_numbers = [number for number in range(1000) if number not in used_numbers]
    password_hash = hash_password(SIM_PASSWORD)
    users: list[User] = []
    for index in range(1, SIM_USER_COUNT + 1):
        role = role_for_index(index)
        status = status_for_index(index)
        user = User(
            login=f"year_sim_{index:03d}",
            email=f"year.sim.{index:03d}@example.com",
            password_hash=password_hash,
            first_name="BMRL",
            last_name=f"Year {index:03d}",
            nickname=f"Year Pilot {index:03d}" if role == Role.pilot else f"Year {role.value.title()} {index:03d}",
            pilot_number=available_numbers[index - 1],
            country=COUNTRIES[index % len(COUNTRIES)],
            sr=round(min(MAX_SR, 4.7 + (index % 36) * 0.28), 1),
            rating=DEFAULT_RATING,
            rating_race_count=0,
            discord=f"year_sim_{index:03d}",
            steam_id=f"year-steam-{index:04d}",
            role=role,
            status=status,
            avatar_color=COLORS[index % len(COLORS)],
            games=user_games(index),
            ban_end=now + timedelta(days=30) if status == UserStatus.banned else None,
            timeout_start=now - timedelta(hours=6) if status == UserStatus.timeout else None,
            timeout_end=now + timedelta(days=3) if status == UserStatus.timeout else None,
        )
        session.add(user)
        users.append(user)
    await session.flush()
    return users


async def create_teams(session, admin: User, users: list[User], now: datetime) -> list[Team]:
    active_users = [user for user in users if user.status == UserStatus.active]
    owners = [admin] + active_users[: SIM_TEAM_COUNT - 1]
    used: set[str] = set()
    teams: list[Team] = []
    for index, name in enumerate(TEAM_NAMES[:SIM_TEAM_COUNT], start=1):
        team = Team(
            name=name,
            abbreviation=team_abbreviation(name, index, used),
            description=f"Year simulation team #{index:02d}.",
            avatar_color=COLORS[(index * 2) % len(COLORS)],
            owner_id=owners[index - 1].id,
            created_at=now - timedelta(days=360 - index),
        )
        session.add(team)
        teams.append(team)
    await session.flush()

    for team, owner in zip(teams, owners, strict=True):
        owner.team_id = team.id

    assigned = {owner.id for owner in owners}
    candidates = [user for user in active_users if user.id not in assigned]
    random.shuffle(candidates)
    for index, user in enumerate(candidates):
        user.team_id = teams[index % len(teams)].id
    await session.flush()
    return teams


def selectable_pilots(users: list[User], game: str) -> list[User]:
    pilots = [user for user in users if user.role == Role.pilot and user.status == UserStatus.active and game in (user.games or [])]
    fallback = [user for user in users if user.role == Role.pilot and user.status == UserStatus.active]
    return pilots or fallback


def result_payload(
    race: Race,
    participants: list[User],
    registrations: dict[int, RaceRegistration],
    catalog: dict,
    team_lookup: dict[int, tuple[str, str]],
    race_index: int,
) -> dict:
    ordered = list(participants)
    random.shuffle(ordered)
    cars = race.allowed_cars or class_cars(catalog, race.game, race.car_class)
    rows: list[dict] = []
    track_seed = sum(ord(char) for char in race.track)
    leader_laps = 22 + (race_index + track_seed) % 38
    base_lap = 83_000 + (track_seed % 32_000)
    base_finish = leader_laps * base_lap

    for raw_position, user in enumerate(ordered, start=1):
        registration = registrations.get(user.id)
        car_model = registration.car_model if registration else cars[(raw_position + race_index) % len(cars)]
        dnf = raw_position > 12 and (raw_position + race_index) % 19 == 0
        lap_count = leader_laps if not dnf else max(1, leader_laps - random.randint(1, 5))
        finish_ms = None if dnf else base_finish + raw_position * random.randint(4500, 12500) + random.randint(0, 4000)
        best_lap = None if dnf else base_lap + random.randint(-1500, 3500) + raw_position * random.randint(20, 95)
        race_number = registration.pilot_number if registration else user.pilot_number
        team_name, team_abbreviation = team_lookup.get(user.team_id or 0, (None, None))
        rows.append(
            {
                "user_id": user.id,
                "login": user.login,
                "nickname": user.nickname,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "pilot_number": race_number,
                "race_number": race_number,
                "avatar_color": user.avatar_color,
                "avatar_url": user.avatar_url,
                "team_id": user.team_id,
                "team_name": team_name,
                "team_abbreviation": team_abbreviation,
                "rating": int(round(float(user.rating))),
                "sr": float(user.sr),
                "country": user.country,
                "driver_name": display_name(user),
                "player_id": f"S{user.steam_id}",
                "car_model": car_model,
                "finish_ms": finish_ms,
                "lap_count": lap_count,
                "best_lap_ms": best_lap,
                "qualification_position": None,
                "qualification_best_lap_ms": None,
                "raw_position": raw_position,
                "source": "lmu_manual" if race.game == "LMU" else race.game.lower(),
                "status": "dnf" if dnf else "classified",
            }
        )

    qualification = None
    if race.has_qualification:
        qualified = sorted(rows, key=lambda row: row["best_lap_ms"] or 999_999_999)
        for position, row in enumerate(qualified, start=1):
            row["qualification_position"] = position
            row["qualification_best_lap_ms"] = row["best_lap_ms"]
        qualification = {
            "session_type": "Q",
            "raw": {"sessionType": "Q", "trackName": race.track, "sessionResult": {"leaderBoardLines": [ms_to_line(row, "Q") for row in qualified]}},
        }

    return {
        "format": "lmu_manual" if race.game == "LMU" else ("acc" if race.game == "ACC" else "manual"),
        "track_id": race.track_id,
        "track": race.track,
        "qualification_enabled": bool(race.has_qualification),
        "qualification": qualification,
        "race": {"session_type": "R", "raw": {"sessionType": "R", "trackName": race.track, "sessionResult": {"leaderBoardLines": [ms_to_line(row, "R") for row in rows]}}},
        "rows": rows,
    }


async def add_registrations(session, race: Race, participants: list[User], catalog: dict, start: datetime) -> dict[int, RaceRegistration]:
    if race.game == "LMU" and race.championship_id is None:
        return {}
    cars = race.allowed_cars or class_cars(catalog, race.game, race.car_class)
    registrations: dict[int, RaceRegistration] = {}
    used_numbers: set[int] = set()
    for index, user in enumerate(participants, start=1):
        number = user.pilot_number if user.pilot_number not in used_numbers else index - 1
        used_numbers.add(number)
        registration = RaceRegistration(
            race_id=race.id,
            user_id=user.id,
            car_model=cars[(index + race.id) % len(cars)],
            pilot_number=number,
            registered_at=start - timedelta(days=random.randint(2, 21), minutes=index * 3),
        )
        session.add(registration)
        registrations[user.id] = registration
    await session.flush()
    return registrations


async def add_penalties(session, admin: User, staff: list[User], race: Race, participants: list[User], race_index: int) -> None:
    if race_index % 3 != 0 or len(participants) < 6:
        return
    issuer = random.choice(staff) if staff else admin
    targets = random.sample(participants, random.randint(2, 6))
    descriptions = [
        "Avoidable contact: time and SR penalty.",
        "Unsafe rejoin: time and SR penalty.",
        "Repeated track limits: time and SR penalty.",
        "Blue flag obstruction: time and SR penalty.",
        "Pit exit line violation: time and SR penalty.",
    ]
    for index, target in enumerate(targets):
        pattern = (race_index + index) % 5
        status = PenaltyStatus.active
        appeal_status = None
        rejection_reason = None
        if pattern == 0:
            status = PenaltyStatus.canceled
            appeal_status = AppealStatus.approved
        elif pattern == 1:
            status = PenaltyStatus.appealed
            appeal_status = AppealStatus.pending
        elif pattern == 2:
            appeal_status = AppealStatus.rejected
            rejection_reason = "Replay confirms the original decision."

        time_penalty = float(random.choice([5000, 8000, 10000, 15000, 20000]))
        sr_penalty = float(random.choice([0.3, 0.5, 1.0, 1.5]))
        penalty = Penalty(
            race_id=race.id,
            issuer_id=issuer.id,
            target_id=target.id,
            penalty_type=PenaltyType.combined,
            penalty_value=time_penalty,
            time_penalty_ms=time_penalty,
            sr_penalty_value=sr_penalty,
            status=status,
            description=descriptions[index % len(descriptions)],
            is_applied=False,
        )
        session.add(penalty)
        await session.flush()
        if appeal_status is not None:
            session.add(
                Appeal(
                    user_id=target.id,
                    race_id=race.id,
                    penalty_id=penalty.id,
                    proof_link=f"https://example.com/replays/year/{race.id}/{penalty.id}",
                    description="Year simulation appeal.",
                    rejection_reason=rejection_reason,
                    status=appeal_status,
                    moderator_id=admin.id if appeal_status != AppealStatus.pending else None,
                )
            )


async def add_fan_vote(session, race: Race, participants: list[User], voters: list[User], now: datetime, race_index: int) -> None:
    if race_index % 7 != 0 or len(participants) < 3:
        return
    options = [user.id for user in participants[:3]]
    race.fan_vote_options = options
    race.fan_vote_started_at = now - timedelta(days=random.randint(3, 45))
    for voter in random.sample(voters, min(len(voters), random.randint(45, 120))):
        session.add(RaceFanVote(race_id=race.id, user_id=voter.id, target_id=random.choices(options, weights=[5, 3, 2])[0]))


async def create_race(
    session,
    admin: User,
    staff: list[User],
    users: list[User],
    catalog: dict,
    team_lookup: dict[int, tuple[str, str]],
    now: datetime,
    game: str,
    start: datetime,
    race_index: int,
    championship: Championship | None = None,
    championship_round: int | None = None,
    participants: list[User] | None = None,
    car_class: str | None = None,
    track: str | None = None,
    status: RaceStatus = RaceStatus.finished,
) -> Race:
    car_class = car_class or random_class(catalog, game)
    cars = class_cars(catalog, game, car_class)
    track = track or random.choice(catalog[game]["tracks"])
    if participants is None:
        pool = selectable_pilots(users, game)
        participants = random.sample(pool, min(len(pool), random.randint(22, 42)))
    max_pilots = 500 if game == "LMU" else max(32, min(80, len(participants) + random.randint(6, 20)))
    end = start + timedelta(hours=2 + race_index % 3)
    race = Race(
        name=f"{championship.name} R{championship_round:02d}" if championship else f"BMRL Year {game} Race {race_index:03d}",
        description=f"Simulated one-year {game} race with generated results.",
        server_link=f"https://example.com/bmrl/{game.lower()}/race-{race_index:03d}",
        lmu_results_at=end if game == "LMU" else None,
        datetime_start=start,
        datetime_end=end,
        max_pilots=max_pilots,
        car_class=car_class,
        track=track,
        track_id=catalog_track_id(catalog, game, track),
        mods_pack=[] if game in {"ACC", "LMU"} else [f"{game} BMRL pack"],
        allowed_cars=[] if game == "LMU" else cars,
        status=status,
        is_passed=status == RaceStatus.finished,
        results=None,
        game=game,
        has_qualification=game != "LMU" and race_index % 2 == 0,
        scoring_system=championship.scoring_system if championship else random.choice(list(ChampionshipScoringSystem)),
        pole_bonus_enabled=championship.pole_bonus_enabled if championship else race_index % 4 == 0,
        championship_id=championship.id if championship else None,
        championship_round=championship_round,
        creator_id=random.choice(staff).id if staff else admin.id,
        is_official=race_index % 5 != 0,
        registered_pilots=[],
        created_at=start - timedelta(days=25),
    )
    session.add(race)
    await session.flush()
    registrations = await add_registrations(session, race, participants, catalog, start)
    if status == RaceStatus.finished:
        race.results = result_payload(race, participants, registrations, catalog, team_lookup, race_index)
        assert_no_zero_times(race.results, f"race:{race.name}")
        await add_penalties(session, admin, staff, race, participants, race_index)
        await add_fan_vote(session, race, participants, [user for user in users if user.status == UserStatus.active], now, race_index)
    return race


async def create_championships(
    session,
    admin: User,
    staff: list[User],
    users: list[User],
    catalog: dict,
    team_lookup: dict[int, tuple[str, str]],
    year_start: datetime,
    now: datetime,
) -> tuple[list[Championship], dict[str, int], list[Race]]:
    championships: list[Championship] = []
    races_by_game = {game: 0 for game in GAMES}
    races: list[Race] = []
    for index, (name, game, car_class, stage_count, scoring, pole_bonus) in enumerate(CHAMPIONSHIP_SPECS, start=1):
        start = year_start + timedelta(days=18 + (index - 1) * 33)
        end = start + timedelta(days=stage_count * 6 + 2)
        cars = class_cars(catalog, game, car_class)
        championship = Championship(
            name=f"{name} 2026",
            description=f"One-year simulated championship #{index}.",
            classes=[car_class],
            registration_start=start - timedelta(days=21),
            registration_end=start - timedelta(days=3),
            championship_start=start,
            championship_end=end,
            video_url=None,
            game=game,
            car_change_allowed=index % 2 == 0,
            default_car=None,
            scoring_system=scoring,
            pole_bonus_enabled=pole_bonus,
            is_published=True,
            creator_id=random.choice(staff).id if staff else admin.id,
            created_at=start - timedelta(days=30),
        )
        session.add(championship)
        await session.flush()

        pool = selectable_pilots(users, game)
        participants = random.sample(pool, min(len(pool), random.randint(28, 44)))
        used_numbers: set[int] = set()
        registrations: dict[int, ChampionshipRegistration] = {}
        for pos, pilot in enumerate(participants, start=1):
            number = pilot.pilot_number if pilot.pilot_number not in used_numbers else pos - 1
            used_numbers.add(number)
            registration = ChampionshipRegistration(
                championship_id=championship.id,
                user_id=pilot.id,
                status=TeamApplicationStatus.approved,
                car_model=cars[(pos + index) % len(cars)],
                pilot_number=number,
                created_at=start - timedelta(days=18, hours=pos),
                resolved_at=start - timedelta(days=17, hours=pos),
                resolved_by=admin.id,
            )
            session.add(registration)
            registrations[pilot.id] = registration
        for pilot in random.sample([user for user in pool if user not in participants], min(6, max(0, len(pool) - len(participants)))):
            session.add(
                ChampionshipRegistration(
                    championship_id=championship.id,
                    user_id=pilot.id,
                    status=random.choice([TeamApplicationStatus.pending, TeamApplicationStatus.rejected]),
                    car_model=random.choice(cars),
                    pilot_number=pilot.pilot_number,
                    created_at=start - timedelta(days=14),
                    resolved_at=start - timedelta(days=13),
                    resolved_by=admin.id,
                )
            )
        await session.flush()

        for round_number in range(1, stage_count + 1):
            stage_start = start + timedelta(days=(round_number - 1) * 6, hours=(round_number * 2) % 20)
            stage = await create_race(
                session,
                admin,
                staff,
                users,
                catalog,
                team_lookup,
                now,
                game,
                stage_start,
                round_number + index * 1000,
                championship,
                round_number,
                participants,
                car_class,
                random.choice(catalog[game]["tracks"]),
            )
            if game != "LMU":
                for race_registration in list(registrations.values()):
                    existing = await session.scalar(
                        select(RaceRegistration).where(
                            RaceRegistration.race_id == stage.id,
                            RaceRegistration.user_id == race_registration.user_id,
                        )
                    )
                    if existing:
                        existing.car_model = race_registration.car_model or existing.car_model
                        existing.pilot_number = race_registration.pilot_number
            races_by_game[game] += 1
            races.append(stage)
        championships.append(championship)
    return championships, races_by_game, races


async def create_regular_races(
    session,
    admin: User,
    staff: list[User],
    users: list[User],
    catalog: dict,
    team_lookup: dict[int, tuple[str, str]],
    year_start: datetime,
    now: datetime,
    existing_counts: dict[str, int],
) -> list[Race]:
    races: list[Race] = []
    for game in GAMES:
        needed = max(0, RACES_PER_GAME - existing_counts.get(game, 0))
        for index in range(1, needed + 1):
            day = 4 + int(index * 356 / max(needed, 1))
            start = year_start + timedelta(days=day, hours=(index * 5 + GAMES.index(game) * 3) % 22)
            race = await create_race(session, admin, staff, users, catalog, team_lookup, now, game, start, index)
            races.append(race)
            existing_counts[game] = existing_counts.get(game, 0) + 1
    return races


async def create_live_races(session, admin: User, staff: list[User], users: list[User], catalog: dict, team_lookup: dict[int, tuple[str, str]], now: datetime) -> list[Race]:
    races: list[Race] = []
    for index in range(1, OPEN_REGISTRATION_RACE_COUNT + 1):
        game = GAMES[(index - 1) % len(GAMES)]
        start = now + timedelta(days=index + 2, hours=index % 6)
        races.append(
            await create_race(
                session,
                admin,
                staff,
                users,
                catalog,
                team_lookup,
                now,
                game,
                start,
                9000 + index,
                status=RaceStatus.registration_open,
            )
        )
    for index in range(1, ONGOING_RACE_COUNT + 1):
        game = GAMES[(index + 1) % len(GAMES)]
        start = now - timedelta(minutes=45 + index * 7)
        races.append(
            await create_race(
                session,
                admin,
                staff,
                users,
                catalog,
                team_lookup,
                now,
                game,
                start,
                9100 + index,
                status=RaceStatus.ongoing,
            )
        )
    return races


async def summarize(session) -> dict:
    races_by_game = {
        game: int(await session.scalar(select(func.count()).select_from(Race).where(Race.game == game)) or 0)
        for game in GAMES
    }
    race_statuses = {
        status.value: int(await session.scalar(select(func.count()).select_from(Race).where(Race.status == status)) or 0)
        for status in RaceStatus
    }
    return {
        "users_total": int(await session.scalar(select(func.count()).select_from(User)) or 0),
        "sim_users_created": int(await session.scalar(select(func.count()).select_from(User).where(User.login.like("year_sim_%"))) or 0),
        "teams": int(await session.scalar(select(func.count()).select_from(Team)) or 0),
        "championships": int(await session.scalar(select(func.count()).select_from(Championship)) or 0),
        "races_total": int(await session.scalar(select(func.count()).select_from(Race)) or 0),
        "races_by_game": races_by_game,
        "race_statuses": race_statuses,
        "registrations": int(await session.scalar(select(func.count()).select_from(RaceRegistration)) or 0),
        "championship_registrations": int(await session.scalar(select(func.count()).select_from(ChampionshipRegistration)) or 0),
        "penalties": int(await session.scalar(select(func.count()).select_from(Penalty)) or 0),
        "appeals": int(await session.scalar(select(func.count()).select_from(Appeal)) or 0),
        "fan_votes": int(await session.scalar(select(func.count()).select_from(RaceFanVote)) or 0),
        "simulation_password": SIM_PASSWORD,
        "admin_preserved": get_settings().admin_login,
    }


def cleanup_files(files: dict[str, list[str]]) -> None:
    for url in files.get("avatars", []):
        remove_avatar_file(url)
    for url in files.get("videos", []):
        remove_race_video_file(url)


async def run() -> dict:
    random.seed(RANDOM_SEED)
    now = datetime.now(timezone.utc)
    year_start = now - timedelta(days=365)
    async with SessionLocal() as session:
        admin = await ensure_admin(session)
        files_to_remove = await wipe_data(session, admin)
        await save_team_limit(session)
        users = await create_users(session, admin, now)
        teams = await create_teams(session, admin, users, now)
        team_lookup = {team.id: (team.name, team.abbreviation) for team in teams}
        asset_config = await get_race_assets(session)
        asset_config = await ensure_sim_race_assets(session, asset_config)
        catalog = asset_catalog(asset_config)
        staff = [user for user in users if user.status == UserStatus.active and user.role in {Role.moder, Role.marshall}]
        _, race_counts, championship_races = await create_championships(session, admin, staff, users, catalog, team_lookup, year_start, now)
        regular_races = await create_regular_races(session, admin, staff, users, catalog, team_lookup, year_start, now, race_counts)
        live_races = await create_live_races(session, admin, staff, users, catalog, team_lookup, now)
        races = championship_races + regular_races + live_races

        for race in sorted(races, key=lambda item: (item.datetime_start, item.id)):
            await apply_sr_penalties(session, race)
            await recalculate_race_results(session, race)
            if race.results is not None:
                assert_no_zero_times(race.results, f"race:{race.name}:recalculated")
        await recalculate_all_ratings(session)
        await session.commit()
        cleanup_files(files_to_remove)
        return await summarize(session)


def main() -> None:
    print(json.dumps(asyncio.run(run()), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
