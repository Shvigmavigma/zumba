import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest import mock

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app import db
from app.models import Championship, ChampionshipRegistration, Race, RaceRegistration, RaceStatus, Role, TeamApplicationStatus, User, UserStatus


START = datetime(2026, 8, 24, 10, tzinfo=timezone.utc)
CAR = "BMW M4 GT3"
APPROVED = TeamApplicationStatus.approved
PENDING = TeamApplicationStatus.pending
REJECTED = TeamApplicationStatus.rejected


def make_pilot(index: int, pilot_number: int) -> User:
    return User(
        login=f"pilot{index}",
        email=f"pilot{index}@example.com",
        password_hash="not-a-real-hash",
        first_name="Pilot",
        last_name=str(index),
        nickname=f"Pilot {index}",
        pilot_number=pilot_number,
        steam_id=f"steam-{index}",
        role=Role.pilot,
        status=UserStatus.active,
    )


def make_race(index: int, creator_id: int) -> Race:
    return Race(
        name=f"Sprint {index}",
        description="",
        server_link="",
        datetime_start=START,
        datetime_end=START + timedelta(hours=1),
        max_pilots=30,
        car_class="GT3",
        track="Monza",
        status=RaceStatus.registration_open,
        creator_id=creator_id,
    )


def make_championship(index: int, creator_id: int) -> Championship:
    return Championship(
        name=f"GT3 Cup {index}",
        registration_start=START,
        registration_end=START + timedelta(days=7),
        championship_start=START + timedelta(days=8),
        championship_end=START + timedelta(days=60),
        creator_id=creator_id,
    )


class InitDbRegistrationNumbersTest(unittest.IsolatedAsyncioTestCase):
    """Runs the real ``init_db`` against a scratch database created next to the configured one."""

    async def asyncSetUp(self):
        url = make_url(db.settings.database_url)
        database_name = f"bmrl_test_{uuid.uuid4().hex[:12]}"
        admin_engine = create_async_engine(url, isolation_level="AUTOCOMMIT", poolclass=NullPool)
        self.addAsyncCleanup(admin_engine.dispose)
        try:
            async with admin_engine.connect() as conn:
                await conn.execute(text(f'CREATE DATABASE "{database_name}"'))
        except OSError as error:
            self.skipTest(f"PostgreSQL is not reachable: {error}")
        self.addAsyncCleanup(self.drop_database, admin_engine, database_name)
        self.engine = create_async_engine(url.set(database=database_name), poolclass=NullPool)
        self.addAsyncCleanup(self.engine.dispose)
        patcher = mock.patch.object(db, "engine", self.engine)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def drop_database(self, admin_engine: AsyncEngine, database_name: str) -> None:
        async with admin_engine.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)'))

    async def add_pilots(self, session: AsyncSession, profile_numbers: list[int]) -> list[User]:
        pilots = [make_pilot(index, number) for index, number in enumerate(profile_numbers)]
        session.add_all(pilots)
        await session.flush()
        return pilots

    async def add_race_registrations(self, profile_numbers: list[int], numbers_by_race: list[list[int]]) -> None:
        """Registers every pilot to every race, in pilot order, with the given race numbers."""
        async with AsyncSession(self.engine) as session:
            pilots = await self.add_pilots(session, profile_numbers)
            for index, race_numbers in enumerate(numbers_by_race):
                race = make_race(index, pilots[0].id)
                session.add(race)
                await session.flush()
                session.add_all(
                    RaceRegistration(race_id=race.id, user_id=pilot.id, car_model=CAR, pilot_number=number)
                    for pilot, number in zip(pilots, race_numbers)
                )
                await session.flush()
            await session.commit()

    async def add_championship_registrations(
        self,
        profile_numbers: list[int],
        entries_by_championship: list[list[tuple[int, TeamApplicationStatus]]],
    ) -> None:
        """Registers every pilot to every championship, in pilot order, with the given (number, status)."""
        async with AsyncSession(self.engine) as session:
            pilots = await self.add_pilots(session, profile_numbers)
            for index, entries in enumerate(entries_by_championship):
                championship = make_championship(index, pilots[0].id)
                session.add(championship)
                await session.flush()
                session.add_all(
                    ChampionshipRegistration(championship_id=championship.id, user_id=pilot.id, status=status, car_model=CAR, pilot_number=number)
                    for pilot, (number, status) in zip(pilots, entries)
                )
                await session.flush()
            await session.commit()

    async def execute(self, statement: str) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(text(statement))

    async def scalars(self, statement: str) -> list:
        async with self.engine.connect() as conn:
            return list((await conn.execute(text(statement))).scalars())

    async def pilot_numbers(self, table: str) -> list[int]:
        return await self.scalars(f"SELECT pilot_number FROM {table} ORDER BY id")

    async def assert_number_rules_exist(self, table: str, check_name: str, index_name: str) -> None:
        self.assertEqual(await self.scalars(f"SELECT conname FROM pg_constraint WHERE conname = '{check_name}'"), [check_name])
        self.assertEqual(await self.scalars(f"SELECT indexname FROM pg_indexes WHERE indexname = '{index_name}'"), [index_name])
        self.assertEqual(
            await self.scalars(f"SELECT is_nullable FROM information_schema.columns WHERE table_name = '{table}' AND column_name = 'pilot_number'"),
            ["NO"],
        )

    async def test_repeated_init_db_keeps_chosen_race_numbers(self):
        # The same number is free to be used again in another race.
        first_race = [901, 144, 95, 999, 1]
        second_race = [1, 901, 7, 144, 500]
        await db.init_db()
        await self.add_race_registrations([10, 20, 30, 40, 50], [first_race, second_race])

        await db.init_db()
        await db.init_db()

        self.assertEqual(await self.pilot_numbers("race_registrations"), first_race + second_race)

    async def test_repeated_init_db_keeps_chosen_championship_numbers(self):
        # A rejected application may share its number with an active one,
        # whichever of the two was created first.
        first_championship = [(144, REJECTED), (144, APPROVED), (901, PENDING), (0, APPROVED)]
        second_championship = [(901, APPROVED), (144, APPROVED), (144, REJECTED), (7, PENDING)]
        await db.init_db()
        await self.add_championship_registrations([10, 20, 30, 40], [first_championship, second_championship])

        await db.init_db()
        await db.init_db()

        self.assertEqual(
            await self.pilot_numbers("championship_registrations"),
            [number for number, _ in first_championship + second_championship],
        )

    async def test_first_migration_numbers_each_race_in_registration_order(self):
        # Before the per-race number existed every registration used the profile
        # number, which is neither unique within a race nor limited to 0..999.
        # The one-time migration therefore hands out 0, 1, 2... per race.
        await db.init_db()
        await self.add_race_registrations([77, 77, 500, 1500, 1, 2], [[1, 2, 3, 4, 5, 6], [1, 2, 3, 4]])
        await self.execute("ALTER TABLE race_registrations DROP COLUMN pilot_number")

        await db.init_db()

        migrated = [0, 1, 2, 3, 4, 5] + [0, 1, 2, 3]
        self.assertEqual(await self.pilot_numbers("race_registrations"), migrated)
        await self.assert_number_rules_exist("race_registrations", "ck_race_registrations_pilot_number_range", "uq_race_registration_race_pilot_number")

        # It runs once: the next start finds the column and leaves it alone.
        await db.init_db()

        self.assertEqual(await self.pilot_numbers("race_registrations"), migrated)

    async def test_first_migration_numbers_each_championship_in_registration_order(self):
        await db.init_db()
        await self.add_championship_registrations(
            [77, 77, 77, 1500, 1],
            [
                [(1, APPROVED), (2, PENDING), (3, REJECTED), (4, APPROVED), (5, APPROVED)],
                [(1, REJECTED), (2, APPROVED), (3, APPROVED), (4, PENDING)],
            ],
        )
        await self.execute("ALTER TABLE championship_registrations DROP COLUMN pilot_number")

        await db.init_db()

        migrated = [0, 1, 2, 3, 4] + [0, 1, 2, 3]
        self.assertEqual(await self.pilot_numbers("championship_registrations"), migrated)
        await self.assert_number_rules_exist(
            "championship_registrations",
            "ck_championship_registrations_pilot_number_range",
            "uq_championship_registration_pilot_number",
        )

        await db.init_db()

        self.assertEqual(await self.pilot_numbers("championship_registrations"), migrated)


if __name__ == "__main__":
    unittest.main()
