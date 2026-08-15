import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import DEFAULT_SR, ChampionshipScoringSystem, Race, RaceRegistration, RaceStatus, Role, User, UserStatus
from app.security import hash_password
from app.services import recalculate_all_ratings, recalculate_race_results


PASSWORD = "TrackDemo2026!"
RACE_PREFIX = "BMRL Track Records Demo"
CARS = [
    "Ferrari 296 GT3 2023",
    "BMW M4 GT3 2021",
    "Porsche 992 GT3R 2023",
    "McLaren 720S Evo GT3 2023",
    "Audi R8 LMS Evo II GT3 2022",
    "Mercedes AMG Evo GT3 2020",
]
RACES = [
    ("ACC", "Spa-Francorchamps", "GT3", 95_200),
    ("ACC", "Monza", "GT3", 108_800),
    ("AC", "Nordschleife", "GT3", 497_000),
    ("iRacing", "Watkins Glen", "GT3", 105_400),
    ("LMU", "Le Mans", "Hypercar", 210_600),
]


async def get_or_create_user(session, index: int) -> User:
    login = f"track_demo_{index:02d}"
    user = await session.scalar(select(User).where(User.login == login))
    if user:
        return user
    user = User(
        login=login,
        email=f"{login}@example.com",
        password_hash=hash_password(PASSWORD),
        first_name="Track",
        last_name=f"Demo {index:02d}",
        nickname=f"Track Demo {index:02d}",
        pilot_number=(520 + index) % 1000,
        country="Global",
        sr=DEFAULT_SR,
        discord=None,
        steam_id=f"track-demo-steam-{index:02d}",
        role=Role.pilot,
        status=UserStatus.active,
        avatar_color="#1652D8",
        games=["ACC", "AC", "iRacing", "LMU"],
    )
    session.add(user)
    await session.flush()
    return user


def result_row(race: Race, user: User, position: int, base_lap_ms: int) -> dict:
    best_lap_ms = base_lap_ms + position * 430 + (race.id % 7) * 38
    lap_count = 22 + position % 4
    finish_ms = best_lap_ms * lap_count + position * 1_450
    return {
        "position": position,
        "raw_position": position,
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
        "team_name": None,
        "team_abbreviation": None,
        "rating": int(round(float(user.rating))),
        "sr": float(user.sr),
        "driver_name": f"{user.first_name} {user.last_name}",
        "car_model": CARS[(position - 1) % len(CARS)],
        "finish_ms": finish_ms,
        "adjusted_finish_ms": finish_ms,
        "lap_count": lap_count,
        "best_lap_ms": best_lap_ms,
        "source": "track_demo",
    }


async def run() -> dict:
    async with SessionLocal() as session:
        users = [await get_or_create_user(session, index) for index in range(1, 19)]
        creator = await session.scalar(select(User).where(User.login == "admin"))
        creator = creator or users[0]

        existing = (await session.scalars(select(Race).where(Race.name.like(f"{RACE_PREFIX}%")))).all()
        if existing:
            await session.execute(delete(RaceRegistration).where(RaceRegistration.race_id.in_([race.id for race in existing])))
            for race in existing:
                await session.delete(race)
            await session.flush()

        now = datetime.now(timezone.utc)
        created = []
        for index, (game, track, car_class, base_lap_ms) in enumerate(RACES, start=1):
            participants = [users[(index + offset - 1) % len(users)] for offset in range(15)]
            race = Race(
                name=f"{RACE_PREFIX} {index:02d} - {track}",
                description="Demo race for the pilots and tracks page.",
                server_link="https://example.com/bmrl/track-records",
                datetime_start=now - timedelta(days=18 - index),
                datetime_end=now - timedelta(days=18 - index, hours=-2),
                max_pilots=32,
                car_class=car_class,
                track=track,
                mods_pack=[],
                allowed_cars=CARS,
                status=RaceStatus.finished,
                is_passed=True,
                results=None,
                game=game,
                has_qualification=game == "ACC",
                scoring_system=ChampionshipScoringSystem.fia,
                pole_bonus_enabled=False,
                championship_id=None,
                championship_round=None,
                creator_id=creator.id,
                is_official=True,
                registered_pilots=[],
            )
            session.add(race)
            await session.flush()
            rows = []
            for position, user in enumerate(participants[:15], start=1):
                car = CARS[(position - 1) % len(CARS)]
                if game != "LMU":
                    session.add(
                        RaceRegistration(
                            race_id=race.id,
                            user_id=user.id,
                            car_model=car,
                            pilot_number=user.pilot_number,
                            registered_at=now - timedelta(days=20 - index, minutes=position),
                        )
                    )
                rows.append(result_row(race, user, position, base_lap_ms))
            race.results = {"format": "track_demo", "track": track, "qualification_enabled": race.has_qualification, "rows": rows}
            await recalculate_race_results(session, race)
            created.append(race.name)

        await recalculate_all_ratings(session)
        await session.commit()
        return {"created_races": created, "demo_password": PASSWORD}


if __name__ == "__main__":
    print(asyncio.run(run()))
