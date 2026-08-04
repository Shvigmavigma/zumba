from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import (
    DEFAULT_SR,
    DEFAULT_USER_GAMES,
    MAX_SR,
    MIN_SR,
    Appeal,
    AppealStatus,
    Banner,
    BannerPosition,
    Penalty,
    PenaltyStatus,
    PenaltyType,
    Race,
    RaceRegistration,
    RaceStatus,
    Role,
    Team,
    User,
    UserStatus,
)
from app.security import hash_password


DEMO_ACCOUNT_PASSWORD = "BmrlDemo2026!"
DEMO_TEAMLESS_LOGIN = "bmrl_teamless"
DEMO_ACCOUNTS = [
    {
        "login": "bmrl_admin",
        "email": "bmrl.admin@example.com",
        "first_name": "BMRL",
        "last_name": "Admin",
        "nickname": "BMRL Admin",
        "pilot_number": 101,
        "steam_id": "bmrl-demo-admin",
        "role": Role.admin,
        "avatar_color": "#dc2626",
        "sr": DEFAULT_SR,
    },
    {
        "login": "bmrl_moder",
        "email": "bmrl.moder@example.com",
        "first_name": "BMRL",
        "last_name": "Moderator",
        "nickname": "BMRL Moder",
        "pilot_number": 102,
        "steam_id": "bmrl-demo-moder",
        "role": Role.moder,
        "avatar_color": "#2454d6",
        "sr": DEFAULT_SR,
    },
    {
        "login": "bmrl_marshall",
        "email": "bmrl.marshall@example.com",
        "first_name": "BMRL",
        "last_name": "Marshall",
        "nickname": "BMRL Marshall",
        "pilot_number": 103,
        "steam_id": "bmrl-demo-marshall",
        "role": Role.marshall,
        "avatar_color": "#15803d",
        "sr": DEFAULT_SR,
    },
    {
        "login": "bmrl_smm",
        "email": "bmrl.smm@example.com",
        "first_name": "BMRL",
        "last_name": "SMM",
        "nickname": "BMRL SMM",
        "pilot_number": 104,
        "steam_id": "bmrl-demo-smm",
        "role": Role.smm,
        "avatar_color": "#9333ea",
        "sr": DEFAULT_SR,
    },
    {
        "login": "bmrl_pilot",
        "email": "bmrl.pilot@example.com",
        "first_name": "BMRL",
        "last_name": "Pilot",
        "nickname": "BMRL Pilot",
        "pilot_number": 105,
        "steam_id": "bmrl-demo-pilot",
        "role": Role.pilot,
        "avatar_color": "#f59e0b",
        "sr": DEFAULT_SR,
    },
    {
        "login": DEMO_TEAMLESS_LOGIN,
        "email": "bmrl.teamless@example.com",
        "first_name": "BMRL",
        "last_name": "Solo",
        "nickname": "BMRL Solo",
        "pilot_number": 301,
        "steam_id": "bmrl-demo-teamless",
        "role": Role.pilot,
        "avatar_color": "#64748b",
        "country": "Global",
        "sr": DEFAULT_SR,
    },
]

DEMO_SCENARIO_PILOTS = [
    {
        "login": f"bmrl_demo_pilot_{index:02d}",
        "email": f"bmrl.demo.pilot.{index:02d}@example.com",
        "first_name": "BMRL",
        "last_name": f"Demo {index:02d}",
        "nickname": f"Demo Pilot {index:02d}",
        "pilot_number": 200 + index,
        "steam_id": f"bmrl-demo-extra-pilot-{index:02d}",
        "role": Role.pilot,
        "avatar_color": color,
        "country": country,
        "sr": min(MAX_SR, DEFAULT_SR + index * 0.6),
    }
    for index, color, country in [
        (1, "#0ea5e9", "Germany"),
        (2, "#22c55e", "Italy"),
        (3, "#f97316", "Spain"),
        (4, "#e11d48", "France"),
        (5, "#8b5cf6", "Poland"),
        (6, "#14b8a6", "Brazil"),
        (7, "#f59e0b", "Japan"),
        (8, "#64748b", "United States"),
    ]
]

DEMO_ACCOUNTS.extend(DEMO_SCENARIO_PILOTS)
DEMO_SCENARIO_PARTICIPANT_LOGINS = ["bmrl_pilot"] + [account["login"] for account in DEMO_SCENARIO_PILOTS]
DEMO_RACE_PREFIX = "BMRL Demo Race"
DEMO_TEAM_SPECS = [
    {
        "name": "BMRL Factory",
        "description": "System-backed factory team for race control checks and admin-owned scenarios.",
        "avatar_color": "#dc2626",
        "owner_login": "admin",
        "member_logins": ["admin", "bmrl_demo_pilot_01", "bmrl_demo_pilot_02"],
    },
    {
        "name": "Apex Line",
        "description": "ACC sprint roster focused on clean qualifying pace and stable race starts.",
        "avatar_color": "#0ea5e9",
        "owner_login": "bmrl_moder",
        "member_logins": ["bmrl_moder", "bmrl_demo_pilot_03", "bmrl_demo_pilot_04"],
    },
    {
        "name": "Curb Hunters",
        "description": "Mixed AC group for track-learning sessions, setups and replay reviews.",
        "avatar_color": "#22c55e",
        "owner_login": "bmrl_marshall",
        "member_logins": ["bmrl_marshall", "bmrl_demo_pilot_05", "bmrl_demo_pilot_06"],
    },
    {
        "name": "Sector Ghosts",
        "description": "iRacing squad that experiments with endurance strategy and stint consistency.",
        "avatar_color": "#8b5cf6",
        "owner_login": "bmrl_smm",
        "member_logins": ["bmrl_smm", "bmrl_demo_pilot_07"],
    },
    {
        "name": "Redline Union",
        "description": "Open community team for pilots who want shared practice and race-day support.",
        "avatar_color": "#f59e0b",
        "owner_login": "bmrl_pilot",
        "member_logins": ["bmrl_pilot", "bmrl_demo_pilot_08"],
    },
]


async def upsert_demo_accounts(session: AsyncSession) -> None:
    for account in DEMO_ACCOUNTS:
        user = await session.scalar(select(User).where(User.login == account["login"]))
        password_hash = hash_password(DEMO_ACCOUNT_PASSWORD)
        games = account.get("games") or DEFAULT_USER_GAMES
        if user is None:
            session.add(
                User(
                    login=account["login"],
                    email=account["email"],
                    password_hash=password_hash,
                    first_name=account["first_name"],
                    last_name=account["last_name"],
                    nickname=account["nickname"],
                    pilot_number=account["pilot_number"],
                    country=account.get("country", "Global"),
                    sr=account["sr"],
                    discord=None,
                    steam_id=account["steam_id"],
                    role=account["role"],
                    status=UserStatus.active,
                    avatar_color=account["avatar_color"],
                    games=list(games),
                )
            )
            continue

        user.email = account["email"]
        user.password_hash = password_hash
        user.first_name = account["first_name"]
        user.last_name = account["last_name"]
        user.nickname = account["nickname"]
        user.pilot_number = account["pilot_number"]
        user.country = account.get("country", "Global")
        user.sr = account["sr"]
        user.discord = None
        user.steam_id = account["steam_id"]
        user.role = account["role"]
        user.status = UserStatus.active
        user.avatar_color = account["avatar_color"]
        user.games = list(games)
        user.ban_end = None
        user.timeout_start = None
        user.timeout_end = None
        user.pending_profile_changes = None


async def seed_demo_teams(session: AsyncSession) -> None:
    logins = sorted({login for team in DEMO_TEAM_SPECS for login in team["member_logins"]} | {team["owner_login"] for team in DEMO_TEAM_SPECS})
    users = (await session.scalars(select(User).where(User.login.in_(logins)))).all()
    users_by_login = {user.login: user for user in users}

    for spec in DEMO_TEAM_SPECS:
        owner = users_by_login.get(spec["owner_login"])
        if owner is None:
            continue

        team = await session.scalar(select(Team).where(Team.name == spec["name"]))
        if team is None:
            team = Team(
                name=spec["name"],
                description=spec["description"],
                avatar_color=spec["avatar_color"],
                owner_id=owner.id,
            )
            session.add(team)
            await session.flush()
        else:
            team.description = spec["description"]
            team.avatar_color = spec["avatar_color"]
            team.owner_id = owner.id

        for login in spec["member_logins"]:
            member = users_by_login.get(login)
            if member is not None:
                member.team_id = team.id

    teamless_user = await session.scalar(select(User).where(User.login == DEMO_TEAMLESS_LOGIN))
    if teamless_user is not None:
        teamless_user.team_id = None


def parse_registered_at(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


async def migrate_json_race_registrations(session: AsyncSession) -> None:
    races = (await session.scalars(select(Race))).all()
    for race in races:
        for item in list(race.registered_pilots or []):
            if not isinstance(item, dict):
                continue
            user_id = item.get("user_id")
            car_model = item.get("car_model")
            if not isinstance(user_id, int) or not isinstance(car_model, str) or not car_model:
                continue
            user = await session.get(User, user_id)
            if user is None:
                continue
            exists = await session.scalar(
                select(RaceRegistration).where(
                    RaceRegistration.race_id == race.id,
                    RaceRegistration.user_id == user_id,
                )
            )
            if exists is not None:
                continue
            session.add(
                RaceRegistration(
                    race_id=race.id,
                    user_id=user_id,
                    car_model=car_model,
                    pilot_number=int(item.get("pilot_number") or user.pilot_number) % 1000,
                    registered_at=parse_registered_at(item.get("registered_at")),
                )
            )


async def normalize_user_sr_values(session: AsyncSession) -> None:
    users = (await session.scalars(select(User))).all()
    for user in users:
        user.sr = min(MAX_SR, max(MIN_SR, float(user.sr)))


def demo_results(race_index: int, participants: list[User]) -> list[dict]:
    return [
        {
            "position": position,
            "user_id": user.id,
            "finish_ms": 1_720_000 + race_index * 8_000 + position * 12_500,
            "laps": 18,
            "car_model": demo_car_for_position(position),
        }
        for position, user in enumerate(participants, start=1)
    ]


def demo_car_for_position(position: int) -> str:
    cars = ["BMW M4 GT3", "Ferrari 296 GT3", "Porsche 992 GT3 R", "Mercedes-AMG GT3", "Audi R8 LMS", "McLaren 720S GT3"]
    return cars[(position - 1) % len(cars)]


async def seed_demo_race_scenario(session: AsyncSession) -> None:
    await session.flush()
    now = datetime.now(timezone.utc)
    race_specs = [
        {
            "name": f"{DEMO_RACE_PREFIX} 01 - Registration Open",
            "description": "Open registration demo race with a full participant list, active penalties and appeals.",
            "status": RaceStatus.registration_open,
            "datetime_start": now + timedelta(days=5),
            "datetime_end": now + timedelta(days=5, hours=3),
            "track": "Spa-Francorchamps",
            "car_class": "GT3",
            "game": "ACC",
        },
        {
            "name": f"{DEMO_RACE_PREFIX} 02 - Late Registration",
            "description": "Second open race used to check scrolling and registration counters on the main menu.",
            "status": RaceStatus.registration_open,
            "datetime_start": now + timedelta(days=3),
            "datetime_end": now + timedelta(days=3, hours=2),
            "track": "Monza",
            "car_class": "GT3",
            "game": "AC",
        },
        {
            "name": f"{DEMO_RACE_PREFIX} 03 - Ongoing",
            "description": "Ongoing race with penalties and appeals for moderation workflow testing.",
            "status": RaceStatus.ongoing,
            "datetime_start": now - timedelta(hours=1),
            "datetime_end": now + timedelta(hours=1),
            "track": "Nurburgring GP",
            "car_class": "GT4",
            "game": "iRacing",
        },
        {
            "name": f"{DEMO_RACE_PREFIX} 04 - Finished",
            "description": "Finished race with results, time penalties, SR penalties and handled appeals.",
            "status": RaceStatus.finished,
            "datetime_start": now - timedelta(hours=6),
            "datetime_end": now - timedelta(hours=4),
            "track": "Brands Hatch",
            "car_class": "GT3",
            "game": "ACC",
        },
        {
            "name": f"{DEMO_RACE_PREFIX} 05 - Finished Endurance",
            "description": "Finished endurance-style demo race with a larger moderation history.",
            "status": RaceStatus.finished,
            "datetime_start": now - timedelta(hours=12),
            "datetime_end": now - timedelta(hours=9),
            "track": "Mount Panorama",
            "car_class": "GT3 Endurance",
            "game": "AC",
        },
    ]
    race_names = {spec["name"] for spec in race_specs}

    existing_demo_races = list((await session.scalars(select(Race).where(Race.name.like(f"{DEMO_RACE_PREFIX}%")))).all())
    existing_race_ids = [race.id for race in existing_demo_races]
    if existing_race_ids:
        await session.execute(delete(Appeal).where(Appeal.race_id.in_(existing_race_ids)))
        await session.execute(delete(Penalty).where(Penalty.race_id.in_(existing_race_ids)))
        await session.execute(delete(RaceRegistration).where(RaceRegistration.race_id.in_(existing_race_ids)))
    for race in existing_demo_races:
        if race.name not in race_names:
            await session.delete(race)
    await session.flush()

    users = list((await session.scalars(select(User).where(User.login.in_(DEMO_SCENARIO_PARTICIPANT_LOGINS + ["bmrl_admin", "bmrl_moder", "bmrl_marshall"])))).all())
    users_by_login = {user.login: user for user in users}
    creator = users_by_login["bmrl_moder"]
    issuer = users_by_login["bmrl_marshall"]
    moderator = users_by_login["bmrl_admin"]
    participant_pool = [users_by_login[login] for login in DEMO_SCENARIO_PARTICIPANT_LOGINS]
    existing_by_name = {race.name: race for race in existing_demo_races if race.name in race_names}

    for race_index, spec in enumerate(race_specs, start=1):
        participants = [participant_pool[(race_index + offset - 1) % len(participant_pool)] for offset in range(6)]
        race = existing_by_name.get(spec["name"])
        if race is None:
            race = Race(
                name=spec["name"],
                description=spec["description"],
                server_link=f"https://example.com/bmrl/demo-race-{race_index:02d}",
                datetime_start=spec["datetime_start"],
                datetime_end=spec["datetime_end"],
                max_pilots=30,
                car_class=spec["car_class"],
                track=spec["track"],
                mods_pack=[],
                allowed_cars=[],
                status=spec["status"],
                is_passed=spec["status"] == RaceStatus.finished,
                results=None,
                game=spec["game"],
                creator_id=creator.id,
                is_official=True,
                registered_pilots=[],
            )
            session.add(race)
            await session.flush()
        else:
            race.description = spec["description"]
            race.server_link = f"https://example.com/bmrl/demo-race-{race_index:02d}"
            race.datetime_start = spec["datetime_start"]
            race.datetime_end = spec["datetime_end"]
            race.max_pilots = 30
            race.car_class = spec["car_class"]
            race.track = spec["track"]
            race.status = spec["status"]
            race.is_passed = spec["status"] == RaceStatus.finished
            race.game = spec["game"]
            race.creator_id = creator.id
            race.is_official = True
            race.registered_pilots = []

        race.mods_pack = ["BMRL demo balance pack", "BMRL race control overlays"]
        race.allowed_cars = [demo_car_for_position(position) for position in range(1, 7)]
        race.results = demo_results(race_index, participants) if spec["status"] != RaceStatus.registration_open else None

        for position, participant in enumerate(participants, start=1):
            session.add(
                RaceRegistration(
                    race_id=race.id,
                    user_id=participant.id,
                    car_model=demo_car_for_position(position),
                    pilot_number=participant.pilot_number,
                    registered_at=now - timedelta(hours=8, minutes=race_index * 9 - position),
                )
            )

        penalties = [
            Penalty(
                race_id=race.id,
                issuer_id=issuer.id,
                target_id=participants[0].id,
                penalty_type=PenaltyType.combined,
                penalty_value=5_000 + race_index * 500,
                time_penalty_ms=5_000 + race_index * 500,
                sr_penalty_value=0.5,
                status=PenaltyStatus.appealed,
                description="Unsafe rejoin after off-track exit: time and SR penalty.",
                is_applied=False,
            ),
            Penalty(
                race_id=race.id,
                issuer_id=issuer.id,
                target_id=participants[1].id,
                penalty_type=PenaltyType.combined,
                penalty_value=5_000,
                time_penalty_ms=5_000,
                sr_penalty_value=0.5,
                status=PenaltyStatus.canceled,
                description="Contact reviewed after appeal and canceled.",
                is_applied=False,
            ),
            Penalty(
                race_id=race.id,
                issuer_id=issuer.id,
                target_id=participants[2].id,
                penalty_type=PenaltyType.combined,
                penalty_value=10_000 + race_index * 750,
                time_penalty_ms=10_000 + race_index * 750,
                sr_penalty_value=1.0,
                status=PenaltyStatus.active,
                description="Avoidable contact in braking zone: time and SR penalty.",
                is_applied=False,
            ),
            Penalty(
                race_id=race.id,
                issuer_id=issuer.id,
                target_id=participants[3].id,
                penalty_type=PenaltyType.combined,
                penalty_value=5_000,
                time_penalty_ms=5_000,
                sr_penalty_value=1.0,
                status=PenaltyStatus.active,
                description="Track limits warning escalated to time and SR penalty.",
                is_applied=False,
            ),
        ]
        session.add_all(penalties)
        await session.flush()

        session.add_all(
            [
                Appeal(
                    user_id=participants[0].id,
                    race_id=race.id,
                    penalty_id=penalties[0].id,
                    proof_link=f"https://example.com/replays/demo-race-{race_index:02d}/unsafe-rejoin",
                    description="Driver claims visibility was blocked and asks for marshal review.",
                    rejection_reason=None,
                    status=AppealStatus.pending,
                    moderator_id=None,
                ),
                Appeal(
                    user_id=participants[1].id,
                    race_id=race.id,
                    penalty_id=penalties[1].id,
                    proof_link=f"https://example.com/replays/demo-race-{race_index:02d}/contact-review",
                    description="Replay shows the other car moved under braking.",
                    rejection_reason=None,
                    status=AppealStatus.approved,
                    moderator_id=moderator.id,
                ),
                Appeal(
                    user_id=participants[2].id,
                    race_id=race.id,
                    penalty_id=penalties[2].id,
                    proof_link=f"https://example.com/replays/demo-race-{race_index:02d}/braking-zone",
                    description="Driver asks to reduce the time penalty.",
                    rejection_reason="Replay confirms avoidable contact.",
                    status=AppealStatus.rejected,
                    moderator_id=moderator.id,
                ),
            ]
        )


async def seed_defaults(session: AsyncSession) -> None:
    settings = get_settings()

    admin = await session.scalar(select(User).where(User.login == settings.admin_login))
    if admin is None:
        session.add(
            User(
                login=settings.admin_login,
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                first_name="System",
                last_name="Admin",
                nickname="Admin",
                pilot_number=1,
                country="Global",
                sr=DEFAULT_SR,
                discord=None,
                steam_id="admin-steam",
                role=Role.admin,
                status=UserStatus.active,
                avatar_color="#ef4444",
                games=list(DEFAULT_USER_GAMES),
            )
        )
    else:
        admin.sr = DEFAULT_SR
        admin.games = list(DEFAULT_USER_GAMES)

    default_banners = {
        BannerPosition.top: ("/assets/banner-top.svg", "#"),
        BannerPosition.bottom: ("/assets/banner-bottom.svg", "#"),
        BannerPosition.left: ("/assets/banner-side.svg", "#"),
        BannerPosition.right: ("/assets/banner-side.svg", "#"),
    }
    for position, (image_url, link_url) in default_banners.items():
        exists = await session.scalar(select(Banner).where(Banner.position == position))
        if exists is None:
            session.add(Banner(position=position, image_url=image_url, link_url=link_url))

    await normalize_user_sr_values(session)
    await migrate_json_race_registrations(session)
    await session.commit()
# zenasy eblan
