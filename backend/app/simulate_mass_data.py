import asyncio
import json
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select, update

from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    AppSetting,
    Appeal,
    AppealStatus,
    Banner,
    DEFAULT_RATING,
    DEFAULT_SR,
    MAX_SR,
    NewsItem,
    Penalty,
    PenaltyStatus,
    PenaltyType,
    Race,
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
from app.security import hash_password
from app.services import apply_sr_penalties, recalculate_all_ratings, recalculate_race_results


SIM_PASSWORD = "BmrlSim2026!"
SIM_USER_COUNT_TOTAL = 200
SIM_TEAM_COUNT = 30
SIM_RACE_COUNT = 50
TEAM_MEMBER_LIMIT = 8
RANDOM_SEED = 26072026

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
]


def team_abbreviation(name: str, index: int, used: set[str] | None = None) -> str:
    raw = "".join(part[0] for part in name.replace("-", " ").split() if part).upper()
    abbreviation = (raw + "XXX")[:3]
    used = used if used is not None else set()
    if abbreviation not in used:
        used.add(abbreviation)
        return abbreviation
    alphabet_index = index % 17576
    while True:
        candidate = "".join(
            chr(65 + value)
            for value in (
                (alphabet_index // 676) % 26,
                (alphabet_index // 26) % 26,
                alphabet_index % 26,
            )
        )
        if candidate not in used:
            used.add(candidate)
            return candidate
        alphabet_index = (alphabet_index + 1) % 17576

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
]

TRACKS = {
    "ACC": [
        "Spa-Francorchamps",
        "Monza",
        "Brands Hatch",
        "Mount Panorama",
        "Nurburgring GP",
        "Kyalami",
        "Zolder",
        "Imola",
    ],
    "AC": [
        "Nordschleife",
        "Red Bull Ring",
        "Silverstone",
        "Laguna Seca",
        "Road America",
        "Donington Park",
        "Okayama",
        "Watkins Glen",
    ],
    "iRacing": [
        "Sebring",
        "Daytona Road",
        "Road Atlanta",
        "Fuji Speedway",
        "Suzuka",
        "Interlagos",
        "Virginia Raceway",
        "Le Mans",
    ],
}

CARS = {
    "ACC": ["BMW M4 GT3", "Ferrari 296 GT3", "Porsche 992 GT3 R", "Mercedes-AMG GT3", "Audi R8 LMS", "McLaren 720S GT3"],
    "AC": ["Porsche 911 RSR", "Ferrari 488 GT3", "BMW M235i", "Mazda MX-5 Cup", "Lotus Evora GTC", "Lamborghini Huracan GT3"],
    "iRacing": ["Mercedes-AMG GT3 2020", "Porsche 911 GT3 R", "Ferrari 296 GT3", "BMW M4 GT4", "Dallara F3", "Mazda MX-5"],
}

COLORS = [
    "#dc2626",
    "#2563eb",
    "#16a34a",
    "#9333ea",
    "#f97316",
    "#0891b2",
    "#be123c",
    "#4f46e5",
    "#0f766e",
    "#ca8a04",
]


def user_games(index: int) -> list[str]:
    variants = [
        ["ACC"],
        ["AC"],
        ["iRacing"],
        ["ACC", "AC"],
        ["ACC", "iRacing"],
        ["AC", "iRacing"],
        ["ACC", "AC", "iRacing"],
    ]
    return variants[index % len(variants)]


def display_name(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip() or user.nickname or user.login


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
            avatar_color="#ef4444",
            games=["ACC", "AC", "iRacing"],
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
    admin.games = ["ACC", "AC", "iRacing"]
    admin.team_id = None
    return admin


async def wipe_simulation_data(session, admin: User) -> None:
    await session.execute(delete(Appeal))
    await session.execute(delete(Penalty))
    await session.execute(delete(RaceRegistration))
    await session.execute(delete(Race))
    await session.execute(delete(Setup))
    await session.execute(delete(TeamApplication))
    await session.execute(delete(TeamCreationRequest))
    await session.execute(update(User).values(team_id=None))
    await session.execute(delete(Team))
    await session.execute(update(Banner).where(Banner.updated_by != admin.id).values(updated_by=None))
    await session.execute(update(NewsItem).where(NewsItem.created_by != admin.id).values(created_by=None))
    await session.execute(delete(User).where(User.id != admin.id))
    await session.flush()


def role_for_index(index: int) -> Role:
    if index == 1:
        return Role.moder
    if index in {2, 3}:
        return Role.marshall
    if index in {4, 5}:
        return Role.smm
    return Role.pilot


def status_for_index(index: int) -> UserStatus:
    if index <= 5:
        return UserStatus.active
    if index % 59 == 0:
        return UserStatus.unapproved
    if index % 53 == 0:
        return UserStatus.timeout
    if index % 47 == 0:
        return UserStatus.banned
    return UserStatus.active


async def create_users(session, now: datetime) -> list[User]:
    users: list[User] = []
    password_hash = hash_password(SIM_PASSWORD)
    for index in range(1, SIM_USER_COUNT_TOTAL):
        role = role_for_index(index)
        status = status_for_index(index)
        user = User(
            login=f"sim_user_{index:03d}",
            email=f"sim.user.{index:03d}@example.com",
            password_hash=password_hash,
            first_name="BMRL",
            last_name=f"Sim {index:03d}",
            nickname=f"Sim Pilot {index:03d}" if role == Role.pilot else f"Sim {role.value.title()} {index:03d}",
            pilot_number=index % 1000,
            country=COUNTRIES[index % len(COUNTRIES)],
            sr=round(min(MAX_SR, 4.5 + (index % 34) * 0.35), 1),
            rating=DEFAULT_RATING,
            rating_race_count=0,
            discord=f"sim_user_{index:03d}",
            steam_id=f"sim-steam-{index:04d}",
            role=role,
            status=status,
            avatar_color=COLORS[index % len(COLORS)],
            games=user_games(index),
            ban_end=now + timedelta(days=7) if status == UserStatus.banned else None,
            timeout_start=now - timedelta(hours=2) if status == UserStatus.timeout else None,
            timeout_end=now + timedelta(days=2) if status == UserStatus.timeout else None,
        )
        session.add(user)
        users.append(user)
    await session.flush()
    return users


async def save_team_limit(session) -> None:
    setting = await session.get(AppSetting, "team_member_limit")
    if setting is None:
        session.add(AppSetting(key="team_member_limit", value={"limit": TEAM_MEMBER_LIMIT}))
    else:
        setting.value = {"limit": TEAM_MEMBER_LIMIT}


async def create_teams(session, admin: User, users: list[User], now: datetime) -> list[Team]:
    active_users = [user for user in users if user.status == UserStatus.active]
    owner_candidates = [admin] + active_users[: SIM_TEAM_COUNT - 1]
    teams: list[Team] = []
    used_abbreviations: set[str] = set()

    for index, name in enumerate(TEAM_NAMES, start=1):
        owner = owner_candidates[index - 1]
        team = Team(
            name=name,
            abbreviation=team_abbreviation(name, index, used_abbreviations),
            description=f"Simulated roster #{index:02d} with mixed pace, applications, and race history.",
            avatar_color=COLORS[(index * 3) % len(COLORS)],
            owner_id=owner.id,
            created_at=now - timedelta(days=90 - index),
        )
        session.add(team)
        teams.append(team)
    await session.flush()

    for team, owner in zip(teams, owner_candidates, strict=True):
        owner.team_id = team.id

    assigned_ids = {owner.id for owner in owner_candidates}
    assignable = [user for user in active_users if user.id not in assigned_ids]
    random.shuffle(assignable)
    for index, team in enumerate(teams):
        target_size = 4 + (index % 5)
        current_size = 1
        while current_size < target_size and assignable:
            member = assignable.pop()
            member.team_id = team.id
            current_size += 1

    for index, team in enumerate(teams[:12], start=1):
        request = TeamCreationRequest(
            requester_id=team.owner_id,
            name=f"{team.name} request",
            abbreviation=team.abbreviation,
            description=team.description,
            avatar_color=team.avatar_color,
            status=TeamApplicationStatus.approved,
            team_id=team.id,
            resolved_at=now - timedelta(days=80 - index),
            resolved_by=admin.id,
        )
        session.add(request)

    teamless = [user for user in active_users if user.team_id is None]
    for index, user in enumerate(teamless[:5], start=1):
        session.add(
            TeamCreationRequest(
                requester_id=user.id,
                name=f"Pending Sim Team {index:02d}",
                abbreviation=team_abbreviation(f"Pending Sim Team {index:02d}", 100 + index, used_abbreviations),
                description="Pending simulated team creation request.",
                avatar_color=COLORS[index % len(COLORS)],
                status=TeamApplicationStatus.pending,
            )
        )
    for index, user in enumerate(teamless[5:10], start=1):
        session.add(
            TeamCreationRequest(
                requester_id=user.id,
                name=f"Rejected Sim Team {index:02d}",
                abbreviation=team_abbreviation(f"Rejected Sim Team {index:02d}", 200 + index, used_abbreviations),
                description="Rejected simulated team creation request.",
                avatar_color=COLORS[(index + 4) % len(COLORS)],
                status=TeamApplicationStatus.rejected,
                resolved_at=now - timedelta(days=index),
                resolved_by=admin.id,
            )
        )

    await session.flush()
    return teams


async def create_team_applications(session, admin: User, teams: list[Team], users: list[User], now: datetime) -> None:
    active_users = [user for user in users if user.status == UserStatus.active]
    members = [user for user in active_users if user.team_id is not None]
    teamless = [user for user in active_users if user.team_id is None]

    for index, user in enumerate(members[:35]):
        session.add(
            TeamApplication(
                team_id=user.team_id,
                user_id=user.id,
                status=TeamApplicationStatus.approved,
                created_at=now - timedelta(days=65, hours=index),
                resolved_at=now - timedelta(days=64, hours=index),
                resolved_by=admin.id,
            )
        )

    for index, user in enumerate(teamless[:25]):
        team = teams[(index * 2) % len(teams)]
        session.add(
            TeamApplication(
                team_id=team.id,
                user_id=user.id,
                status=TeamApplicationStatus.pending,
                created_at=now - timedelta(hours=index + 1),
            )
        )

    rejected_candidates = list(teamless[25:50])
    if len(rejected_candidates) < 25:
        used_ids = {user.id for user in rejected_candidates}
        rejected_candidates.extend([user for user in active_users if user.id not in used_ids][: 25 - len(rejected_candidates)])

    for index, user in enumerate(rejected_candidates[:25]):
        team = teams[(index * 3 + 1) % len(teams)]
        if user.team_id == team.id:
            team = teams[(index * 3 + 2) % len(teams)]
        session.add(
            TeamApplication(
                team_id=team.id,
                user_id=user.id,
                status=TeamApplicationStatus.rejected,
                created_at=now - timedelta(days=index + 1),
                resolved_at=now - timedelta(days=index),
                resolved_by=admin.id,
            )
        )


def selected_participants(pool: list[User], game: str, count: int) -> list[User]:
    matching = [user for user in pool if game in (user.games or [])]
    source = matching if len(matching) >= count else pool
    return random.sample(source, min(count, len(source)))


def leaderboard_lines(rows: list[dict], session_type: str) -> list[dict]:
    lines = []
    for row in rows:
        player_id = str(row.get("player_id") or "").lstrip("S")
        lines.append(
            {
                "car": {
                    "carModel": row.get("car_model"),
                    "raceNumber": row.get("race_number"),
                    "drivers": [
                        {
                            "firstName": row.get("first_name", "BMRL"),
                            "lastName": row.get("last_name", "Driver"),
                            "shortName": row.get("nickname", "SIM")[:3].upper(),
                            "playerId": f"S{player_id}",
                        }
                    ],
                },
                "currentDriver": {
                    "firstName": row.get("first_name", "BMRL"),
                    "lastName": row.get("last_name", "Driver"),
                    "shortName": row.get("nickname", "SIM")[:3].upper(),
                    "playerId": f"S{player_id}",
                },
                "timing": {
                    "bestLap": row.get("best_lap_ms"),
                    "totalTime": row.get("finish_ms") if session_type == "R" else row.get("best_lap_ms"),
                    "lapCount": row.get("lap_count") or 0,
                },
            }
        )
    return lines


def race_results_payload(race: Race, participants: list[User], race_index: int) -> dict:
    ordered = list(participants)
    random.shuffle(ordered)
    rows: list[dict] = []
    base_finish = 2_350_000 + race_index * 17_000
    leader_laps = 24 + race_index % 18
    for raw_position, user in enumerate(ordered, start=1):
        car_model = CARS[race.game][(raw_position + race_index) % len(CARS[race.game])]
        dnf = raw_position > 8 and (raw_position + race_index) % 13 == 0
        finish_ms = None if dnf else base_finish + raw_position * random.randint(5500, 14500) + random.randint(0, 3500)
        best_lap = None if dnf else 91_000 + random.randint(0, 12_000) + raw_position * 110
        rows.append(
            {
                "user_id": user.id,
                "login": user.login,
                "nickname": user.nickname,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "driver_name": display_name(user),
                "player_id": f"S{user.steam_id}",
                "race_number": user.pilot_number,
                "car_model": car_model,
                "finish_ms": finish_ms,
                "lap_count": leader_laps if not dnf else max(0, leader_laps - random.randint(1, 4)),
                "best_lap_ms": best_lap,
                "qualification_position": None,
                "qualification_best_lap_ms": None,
                "raw_position": raw_position,
                "source": race.game.lower(),
                "status": "dnf" if dnf else "classified",
            }
        )

    qualification = None
    if race.game == "ACC" and race.has_qualification:
        qualified = sorted(rows, key=lambda row: row["best_lap_ms"] or 999_999)
        for position, row in enumerate(qualified, start=1):
            row["qualification_position"] = position
            row["qualification_best_lap_ms"] = row["best_lap_ms"]
        qualification = {
            "session_type": "Q",
            "raw": {
                "sessionType": "Q",
                "trackName": race.track,
                "sessionResult": {
                    "leaderBoardLines": leaderboard_lines(qualified, "Q"),
                },
            },
        }

    return {
        "format": "acc" if race.game == "ACC" else "manual",
        "track": race.track,
        "qualification_enabled": race.has_qualification,
        "qualification": qualification,
        "race": {
            "session_type": "R",
            "raw": {
                "sessionType": "R",
                "trackName": race.track,
                "sessionResult": {
                    "leaderBoardLines": leaderboard_lines(rows, "R"),
                },
            },
        },
        "rows": rows,
    }


async def create_race_penalties(session, admin: User, staff: list[User], race: Race, participants: list[User], race_index: int) -> None:
    if race.status == RaceStatus.registration_open:
        return

    issuer = staff[race_index % len(staff)] if staff else admin
    moderator = admin
    target_count = min(len(participants), random.randint(2, 6))
    targets = random.sample(participants, target_count)
    descriptions = [
        "Avoidable contact in braking zone: time and SR penalty.",
        "Unsafe rejoin after leaving the track: time and SR penalty.",
        "Repeated track limits after warning: time and SR penalty.",
        "Blue flag obstruction during race stint: time and SR penalty.",
        "Formation lap violation: time and SR penalty.",
        "Pit exit line violation: time and SR penalty.",
    ]
    for index, target in enumerate(targets):
        pattern = (race_index + index) % 5
        if pattern == 0:
            status = PenaltyStatus.canceled
            appeal_status = AppealStatus.approved
            rejection_reason = None
        elif pattern == 1:
            status = PenaltyStatus.appealed
            appeal_status = AppealStatus.pending
            rejection_reason = None
        elif pattern == 2:
            status = PenaltyStatus.active
            appeal_status = AppealStatus.rejected
            rejection_reason = "Replay confirms the original steward decision."
        else:
            status = PenaltyStatus.active
            appeal_status = None
            rejection_reason = None

        time_penalty = float(random.choice([5000, 8000, 10000, 15000, 20000]))
        sr_penalty = float(random.choice([0.5, 1.0, 1.5]))
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
                    proof_link=f"https://example.com/replays/sim-race-{race_index:02d}/penalty-{penalty.id}",
                    description="Simulated appeal with replay link and steward notes.",
                    rejection_reason=rejection_reason,
                    status=appeal_status,
                    moderator_id=moderator.id if appeal_status != AppealStatus.pending else None,
                )
            )


async def create_races(session, admin: User, users: list[User], now: datetime) -> list[Race]:
    active_pilots = [user for user in users if user.status == UserStatus.active and user.role == Role.pilot]
    staff = [user for user in users if user.status == UserStatus.active and user.role in {Role.moder, Role.marshall}]
    games = ["ACC", "AC", "iRacing"]
    races: list[Race] = []

    for index in range(1, SIM_RACE_COUNT + 1):
        if index <= 36:
            status = RaceStatus.finished
            start = now - timedelta(days=SIM_RACE_COUNT - index + 4, hours=index % 5)
            end = start + timedelta(hours=2 + index % 3)
        elif index <= 43:
            status = RaceStatus.ongoing
            start = now - timedelta(hours=2 + index % 4)
            end = now + timedelta(hours=1 + index % 3)
        else:
            status = RaceStatus.registration_open
            start = now + timedelta(days=index - 43, hours=index % 4)
            end = start + timedelta(hours=2 + index % 2)

        game = games[index % len(games)]
        participants = selected_participants(active_pilots, game, random.randint(12, 28))
        max_pilots = min(60, max(len(participants) + random.randint(4, 18), 20))
        has_qualification = game == "ACC" and index % 2 == 0
        race = Race(
            name=f"BMRL Sim Race {index:02d}",
            description=f"Simulated {game} race #{index:02d} with registrations, moderation history and rating data.",
            server_link=f"https://example.com/bmrl/sim-race-{index:02d}",
            datetime_start=start,
            datetime_end=end,
            max_pilots=max_pilots,
            car_class="GT3" if game == "ACC" else random.choice(["GT3", "GT4", "Cup", "Prototype"]),
            track=random.choice(TRACKS[game]),
            mods_pack=[f"{game} balance pack", "BMRL overlay pack"] if game != "ACC" else ["BMRL steward overlay"],
            allowed_cars=CARS[game],
            status=status,
            is_passed=status == RaceStatus.finished,
            results=None,
            game=game,
            has_qualification=has_qualification,
            creator_id=(staff[index % len(staff)].id if staff else admin.id),
            is_official=index % 3 != 0,
            registered_pilots=[],
            created_at=start - timedelta(days=10),
        )
        session.add(race)
        await session.flush()

        for position, user in enumerate(participants, start=1):
            session.add(
                RaceRegistration(
                    race_id=race.id,
                    user_id=user.id,
                    car_model=CARS[game][position % len(CARS[game])],
                    pilot_number=user.pilot_number,
                    registered_at=start - timedelta(days=random.randint(1, 14), minutes=position * 3),
                )
            )

        if status == RaceStatus.finished:
            race.results = race_results_payload(race, participants, index)

        await create_race_penalties(session, admin, staff, race, participants, index)
        races.append(race)

    await session.flush()
    return races


async def summarize(session) -> dict:
    statuses = {}
    for status in RaceStatus:
        statuses[status.value] = int(
            await session.scalar(select(func.count()).select_from(Race).where(Race.status == status)) or 0
        )
    team_applications = {}
    for status in TeamApplicationStatus:
        team_applications[status.value] = int(
            await session.scalar(select(func.count()).select_from(TeamApplication).where(TeamApplication.status == status)) or 0
        )
    team_creation_requests = {}
    for status in TeamApplicationStatus:
        team_creation_requests[status.value] = int(
            await session.scalar(select(func.count()).select_from(TeamCreationRequest).where(TeamCreationRequest.status == status)) or 0
        )
    appeals = {}
    for status in AppealStatus:
        appeals[status.value] = int(
            await session.scalar(select(func.count()).select_from(Appeal).where(Appeal.status == status)) or 0
        )

    return {
        "users": int(await session.scalar(select(func.count()).select_from(User)) or 0),
        "teams": int(await session.scalar(select(func.count()).select_from(Team)) or 0),
        "races": int(await session.scalar(select(func.count()).select_from(Race)) or 0),
        "race_statuses": statuses,
        "registrations": int(await session.scalar(select(func.count()).select_from(RaceRegistration)) or 0),
        "penalties": int(await session.scalar(select(func.count()).select_from(Penalty)) or 0),
        "appeals": appeals,
        "team_applications": team_applications,
        "team_creation_requests": team_creation_requests,
        "simulation_password": SIM_PASSWORD,
        "admin_owned_team": "BMRL Factory",
    }


async def run() -> dict:
    random.seed(RANDOM_SEED)
    now = datetime.now(timezone.utc)
    async with SessionLocal() as session:
        admin = await ensure_admin(session)
        await wipe_simulation_data(session, admin)
        await save_team_limit(session)
        users = await create_users(session, now)
        teams = await create_teams(session, admin, users, now)
        await create_team_applications(session, admin, teams, users, now)
        races = await create_races(session, admin, users, now)

        for race in races:
            await apply_sr_penalties(session, race)
            if race.results is not None:
                await recalculate_race_results(session, race)
        await recalculate_all_ratings(session)
        await session.commit()
        return await summarize(session)


def main() -> None:
    print(json.dumps(asyncio.run(run()), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
