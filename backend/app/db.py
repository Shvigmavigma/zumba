from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
DB_INIT_LOCK_ID = 75420260721


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@asynccontextmanager
async def db_initialization_lock():
    async with engine.connect() as conn:
        await conn.execute(text("SELECT pg_advisory_lock(:lock_id)"), {"lock_id": DB_INIT_LOCK_ID})
        try:
            yield
        finally:
            await conn.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": DB_INIT_LOCK_ID})


async def init_db() -> None:
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS games JSONB"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS team_id INTEGER"))
        await conn.execute(text("""UPDATE users SET games = '["ACC", "AC", "iRacing"]'::jsonb WHERE games IS NULL OR jsonb_typeof(games) <> 'array'"""))
        await conn.execute(text("""ALTER TABLE users ALTER COLUMN games SET DEFAULT '["ACC", "AC", "iRacing"]'::jsonb"""))
        await conn.execute(text("ALTER TABLE users ALTER COLUMN games SET NOT NULL"))
        await conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'fk_users_team_id'
                    ) THEN
                        ALTER TABLE users
                        ADD CONSTRAINT fk_users_team_id
                        FOREIGN KEY (team_id) REFERENCES teams(id)
                        ON DELETE SET NULL;
                    END IF;
                END $$;
                """
            )
        )
        await conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'fk_teams_owner_id'
                    ) THEN
                        ALTER TABLE teams
                        ADD CONSTRAINT fk_teams_owner_id
                        FOREIGN KEY (owner_id) REFERENCES users(id)
                        ON DELETE SET NULL;
                    END IF;
                END $$;
                """
            )
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_team_id ON users (team_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_teams_owner_id ON teams (owner_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_team_creation_requests_status_created ON team_creation_requests (status, created_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_team_creation_requests_requester_status ON team_creation_requests (requester_id, status)"))
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_team_creation_request_pending_user
                ON team_creation_requests (requester_id)
                WHERE status = 'pending'
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_team_creation_request_pending_name
                ON team_creation_requests (name)
                WHERE status = 'pending'
                """
            )
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_team_applications_team_status_created ON team_applications (team_id, status, created_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_team_applications_user_status ON team_applications (user_id, status)"))
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_team_application_pending_team_user
                ON team_applications (team_id, user_id)
                WHERE status = 'pending'
                """
            )
        )
        await conn.execute(
            text(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES ('team_member_limit', '{"limit": 5}'::jsonb, NOW())
                ON CONFLICT (key) DO NOTHING
                """
            )
        )
        await conn.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_sr_range"))
        await conn.execute(text("UPDATE users SET sr = LEAST(30.0, GREATEST(0.0, sr)) WHERE sr < 0.0 OR sr > 30.0"))
        await conn.execute(text("ALTER TABLE users ADD CONSTRAINT ck_users_sr_range CHECK (sr >= 0.0 AND sr <= 30.0)"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS rating NUMERIC(8, 2) DEFAULT 1000"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS rating_race_count INTEGER DEFAULT 0"))
        await conn.execute(text("UPDATE users SET rating = 1000 WHERE rating IS NULL"))
        await conn.execute(text("UPDATE users SET rating_race_count = 0 WHERE rating_race_count IS NULL"))
        await conn.execute(text("ALTER TABLE users ALTER COLUMN rating SET DEFAULT 1000"))
        await conn.execute(text("ALTER TABLE users ALTER COLUMN rating_race_count SET DEFAULT 0"))
        await conn.execute(text("ALTER TABLE users ALTER COLUMN rating SET NOT NULL"))
        await conn.execute(text("ALTER TABLE users ALTER COLUMN rating_race_count SET NOT NULL"))
        await conn.execute(text("UPDATE users SET rating = ROUND(rating) WHERE rating != ROUND(rating)"))
        await conn.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_rating_range"))
        await conn.execute(text("UPDATE users SET rating = LEAST(10000.0, GREATEST(10.0, rating)) WHERE rating < 10.0 OR rating > 10000.0"))
        await conn.execute(text("ALTER TABLE users ADD CONSTRAINT ck_users_rating_range CHECK (rating >= 10.0 AND rating <= 10000.0)"))
        await conn.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_rating_race_count"))
        await conn.execute(text("UPDATE users SET rating_race_count = 0 WHERE rating_race_count < 0"))
        await conn.execute(text("ALTER TABLE users ADD CONSTRAINT ck_users_rating_race_count CHECK (rating_race_count >= 0)"))
        await conn.execute(text("ALTER TABLE penalties ADD COLUMN IF NOT EXISTS sr_applied_value NUMERIC DEFAULT 0"))
        await conn.execute(text("ALTER TABLE penalties DROP CONSTRAINT IF EXISTS penalties_penalty_type_check"))
        await conn.execute(text("ALTER TABLE penalties ADD COLUMN IF NOT EXISTS time_penalty_ms NUMERIC DEFAULT 0"))
        await conn.execute(text("ALTER TABLE penalties ADD COLUMN IF NOT EXISTS sr_penalty_value NUMERIC DEFAULT 0"))
        await conn.execute(text("UPDATE penalties SET time_penalty_ms = 0 WHERE time_penalty_ms IS NULL"))
        await conn.execute(text("UPDATE penalties SET sr_penalty_value = 0 WHERE sr_penalty_value IS NULL"))
        await conn.execute(
            text(
                """
                UPDATE penalties
                SET time_penalty_ms = penalty_value
                WHERE penalty_type = 'time'
                    AND COALESCE(time_penalty_ms, 0) = 0
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE penalties
                SET sr_penalty_value = penalty_value
                WHERE penalty_type = 'sr'
                    AND COALESCE(sr_penalty_value, 0) = 0
                """
            )
        )
        await conn.execute(text("ALTER TABLE penalties ALTER COLUMN time_penalty_ms SET DEFAULT 0"))
        await conn.execute(text("ALTER TABLE penalties ALTER COLUMN sr_penalty_value SET DEFAULT 0"))
        await conn.execute(text("ALTER TABLE penalties ALTER COLUMN time_penalty_ms SET NOT NULL"))
        await conn.execute(text("ALTER TABLE penalties ALTER COLUMN sr_penalty_value SET NOT NULL"))
        await conn.execute(text("UPDATE penalties SET sr_applied_value = 0 WHERE sr_applied_value IS NULL"))
        await conn.execute(
            text(
                """
                UPDATE penalties
                SET sr_applied_value = penalty_value
                WHERE penalty_type = 'sr'
                    AND is_applied IS TRUE
                    AND sr_applied_value = 0
                """
            )
        )
        await conn.execute(text("ALTER TABLE penalties ALTER COLUMN sr_applied_value SET DEFAULT 0"))
        await conn.execute(text("ALTER TABLE penalties ALTER COLUMN sr_applied_value SET NOT NULL"))
        await conn.execute(text("ALTER TABLE races ADD COLUMN IF NOT EXISTS has_qualification BOOLEAN DEFAULT TRUE"))
        await conn.execute(text("ALTER TABLE races ADD COLUMN IF NOT EXISTS rating_applied BOOLEAN DEFAULT FALSE"))
        await conn.execute(text("UPDATE races SET has_qualification = TRUE WHERE has_qualification IS NULL"))
        await conn.execute(text("UPDATE races SET rating_applied = FALSE WHERE rating_applied IS NULL"))
        await conn.execute(text("ALTER TABLE races ALTER COLUMN has_qualification SET DEFAULT TRUE"))
        await conn.execute(text("ALTER TABLE races ALTER COLUMN rating_applied SET DEFAULT FALSE"))
        await conn.execute(text("ALTER TABLE races ALTER COLUMN has_qualification SET NOT NULL"))
        await conn.execute(text("ALTER TABLE races ALTER COLUMN rating_applied SET NOT NULL"))
        await conn.execute(text("ALTER TABLE races ALTER COLUMN game SET DEFAULT 'ACC'"))
        await conn.execute(
            text(
                """
                UPDATE races
                SET game = CASE
                    WHEN game IN ('ACC', 'Assetto Corsa Competizione') THEN 'ACC'
                    WHEN game IN ('AC', 'Assetto Corsa') THEN 'AC'
                    WHEN lower(game) IN ('iracing', 'iracin') THEN 'iRacing'
                    ELSE 'ACC'
                END
                WHERE game IS NULL OR game NOT IN ('ACC', 'AC', 'iRacing')
                """
            )
        )
