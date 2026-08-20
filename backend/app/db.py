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
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_upload_count INTEGER DEFAULT 0"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_upload_window_start TIMESTAMP WITH TIME ZONE"))
        await conn.execute(text("UPDATE users SET avatar_upload_count = 0 WHERE avatar_upload_count IS NULL"))
        await conn.execute(text("ALTER TABLE users ALTER COLUMN avatar_upload_count SET DEFAULT 0"))
        await conn.execute(text("ALTER TABLE users ALTER COLUMN avatar_upload_count SET NOT NULL"))
        await conn.execute(text("ALTER TABLE teams ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE teams ADD COLUMN IF NOT EXISTS avatar_upload_count INTEGER DEFAULT 0"))
        await conn.execute(text("ALTER TABLE teams ADD COLUMN IF NOT EXISTS avatar_upload_window_start TIMESTAMP WITH TIME ZONE"))
        await conn.execute(text("ALTER TABLE teams ADD COLUMN IF NOT EXISTS abbreviation VARCHAR(3)"))
        await conn.execute(
            text(
                """
                DO $$
                DECLARE
                    team_row RECORD;
                    seed INTEGER;
                    candidate TEXT;
                BEGIN
                    FOR team_row IN
                        SELECT id
                        FROM teams
                        WHERE abbreviation IS NULL OR abbreviation !~ '^[A-Z]{3}$'
                        ORDER BY id
                    LOOP
                        seed := team_row.id % 17576;
                        LOOP
                            candidate :=
                                chr(65 + ((seed / 676)::INTEGER % 26)) ||
                                chr(65 + ((seed / 26)::INTEGER % 26)) ||
                                chr(65 + (seed % 26));
                            EXIT WHEN NOT EXISTS (
                                SELECT 1 FROM teams WHERE id <> team_row.id AND abbreviation = candidate
                            );
                            seed := (seed + 1) % 17576;
                        END LOOP;
                        UPDATE teams SET abbreviation = candidate WHERE id = team_row.id;
                    END LOOP;
                END $$;
                """
            )
        )
        await conn.execute(text("ALTER TABLE teams ALTER COLUMN abbreviation SET NOT NULL"))
        await conn.execute(text("ALTER TABLE teams DROP CONSTRAINT IF EXISTS ck_teams_abbreviation_format"))
        await conn.execute(text("ALTER TABLE teams ADD CONSTRAINT ck_teams_abbreviation_format CHECK (abbreviation ~ '^[A-Z]{3}$')"))
        await conn.execute(text("UPDATE teams SET avatar_upload_count = 0 WHERE avatar_upload_count IS NULL"))
        await conn.execute(text("ALTER TABLE teams ALTER COLUMN avatar_upload_count SET DEFAULT 0"))
        await conn.execute(text("ALTER TABLE teams ALTER COLUMN avatar_upload_count SET NOT NULL"))
        await conn.execute(text("ALTER TABLE team_creation_requests ADD COLUMN IF NOT EXISTS abbreviation VARCHAR(3)"))
        await conn.execute(
            text(
                """
                DO $$
                DECLARE
                    request_row RECORD;
                    seed INTEGER;
                    candidate TEXT;
                BEGIN
                    FOR request_row IN
                        SELECT id
                        FROM team_creation_requests
                        WHERE abbreviation IS NULL OR abbreviation !~ '^[A-Z]{3}$'
                        ORDER BY id
                    LOOP
                        seed := request_row.id % 17576;
                        LOOP
                            candidate :=
                                chr(65 + ((seed / 676)::INTEGER % 26)) ||
                                chr(65 + ((seed / 26)::INTEGER % 26)) ||
                                chr(65 + (seed % 26));
                            EXIT WHEN NOT EXISTS (
                                SELECT 1
                                FROM team_creation_requests
                                WHERE id <> request_row.id
                                  AND status = 'pending'
                                  AND abbreviation = candidate
                            )
                            AND NOT EXISTS (
                                SELECT 1 FROM teams WHERE abbreviation = candidate
                            );
                            seed := (seed + 1) % 17576;
                        END LOOP;
                        UPDATE team_creation_requests SET abbreviation = candidate WHERE id = request_row.id;
                    END LOOP;
                END $$;
                """
            )
        )
        await conn.execute(text("ALTER TABLE team_creation_requests ALTER COLUMN abbreviation SET NOT NULL"))
        await conn.execute(text("ALTER TABLE team_creation_requests DROP CONSTRAINT IF EXISTS ck_team_creation_requests_abbreviation_format"))
        await conn.execute(text("ALTER TABLE team_creation_requests ADD CONSTRAINT ck_team_creation_requests_abbreviation_format CHECK (abbreviation ~ '^[A-Z]{3}$')"))
        await conn.execute(text("ALTER TABLE races ADD COLUMN IF NOT EXISTS video_url VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE races ADD COLUMN IF NOT EXISTS video_filename VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE races ADD COLUMN IF NOT EXISTS video_uploaded_at TIMESTAMP WITH TIME ZONE"))
        await conn.execute(text("ALTER TABLE races ADD COLUMN IF NOT EXISTS fan_vote_options JSONB DEFAULT '[]'::jsonb"))
        await conn.execute(text("ALTER TABLE races ADD COLUMN IF NOT EXISTS fan_vote_started_at TIMESTAMP WITH TIME ZONE"))
        await conn.execute(text("UPDATE races SET fan_vote_options = '[]'::jsonb WHERE fan_vote_options IS NULL OR jsonb_typeof(fan_vote_options) <> 'array'"))
        await conn.execute(text("ALTER TABLE races ALTER COLUMN fan_vote_options SET DEFAULT '[]'::jsonb"))
        await conn.execute(text("ALTER TABLE races ALTER COLUMN fan_vote_options SET NOT NULL"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS games JSONB"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS team_id INTEGER"))
        await conn.execute(text("""UPDATE users SET games = '["ACC", "AC", "iRacing", "LMU"]'::jsonb WHERE games IS NULL OR jsonb_typeof(games) <> 'array'"""))
        await conn.execute(text("""ALTER TABLE users ALTER COLUMN games SET DEFAULT '["ACC", "AC", "iRacing", "LMU"]'::jsonb"""))
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
        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_teams_abbreviation ON teams (abbreviation)"))
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
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_team_creation_request_pending_abbreviation
                ON team_creation_requests (abbreviation)
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
        await conn.execute(
            text(
                """
                ALTER TABLE users ADD COLUMN IF NOT EXISTS game_ratings JSONB DEFAULT
                jsonb_build_object('ACC', jsonb_build_object('rating', 1000, 'race_count', 0), 'AC', jsonb_build_object('rating', 1000, 'race_count', 0), 'iRacing', jsonb_build_object('rating', 1000, 'race_count', 0), 'LMU', jsonb_build_object('rating', 1000, 'race_count', 0))
                """
            )
        )
        await conn.execute(text("UPDATE users SET rating = 1000 WHERE rating IS NULL"))
        await conn.execute(text("UPDATE users SET rating_race_count = 0 WHERE rating_race_count IS NULL"))
        await conn.execute(
            text(
                """
                UPDATE users
                SET game_ratings = jsonb_build_object(
                    'ACC', COALESCE(game_ratings->'ACC', jsonb_build_object('rating', ROUND(rating)::int, 'race_count', rating_race_count)),
                    'AC', COALESCE(game_ratings->'AC', jsonb_build_object('rating', ROUND(rating)::int, 'race_count', rating_race_count)),
                    'iRacing', COALESCE(game_ratings->'iRacing', jsonb_build_object('rating', ROUND(rating)::int, 'race_count', rating_race_count)),
                    'LMU', COALESCE(game_ratings->'LMU', jsonb_build_object('rating', ROUND(rating)::int, 'race_count', rating_race_count))
                )
                WHERE game_ratings IS NULL
                    OR NOT (game_ratings ? 'ACC')
                    OR NOT (game_ratings ? 'AC')
                    OR NOT (game_ratings ? 'iRacing')
                    OR NOT (game_ratings ? 'LMU')
                """
            )
        )
        await conn.execute(text("ALTER TABLE users ALTER COLUMN rating SET DEFAULT 1000"))
        await conn.execute(text("ALTER TABLE users ALTER COLUMN rating_race_count SET DEFAULT 0"))
        await conn.execute(
            text(
                """
                ALTER TABLE users ALTER COLUMN game_ratings SET DEFAULT
                jsonb_build_object('ACC', jsonb_build_object('rating', 1000, 'race_count', 0), 'AC', jsonb_build_object('rating', 1000, 'race_count', 0), 'iRacing', jsonb_build_object('rating', 1000, 'race_count', 0), 'LMU', jsonb_build_object('rating', 1000, 'race_count', 0))
                """
            )
        )
        await conn.execute(text("ALTER TABLE users ALTER COLUMN rating SET NOT NULL"))
        await conn.execute(text("ALTER TABLE users ALTER COLUMN rating_race_count SET NOT NULL"))
        await conn.execute(text("ALTER TABLE users ALTER COLUMN game_ratings SET NOT NULL"))
        await conn.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_pilot_number_key"))
        await conn.execute(text("DROP INDEX IF EXISTS ix_users_pilot_number"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_pilot_number ON users (pilot_number)"))
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
        await conn.execute(text("ALTER TABLE races ADD COLUMN IF NOT EXISTS lmu_results_at TIMESTAMP WITH TIME ZONE"))
        await conn.execute(text("ALTER TABLE races ADD COLUMN IF NOT EXISTS track_id VARCHAR(80)"))
        await conn.execute(
            text(
                """
                WITH asset_track_ids AS (
                    SELECT game.key AS game, lower(track_id.key) AS track_name, track_id.value AS track_id
                    FROM app_settings setting
                    CROSS JOIN LATERAL jsonb_each(COALESCE(setting.value->'games', '{}'::jsonb)) AS game(key, value)
                    CROSS JOIN LATERAL jsonb_each_text(COALESCE(game.value->'track_ids', '{}'::jsonb)) AS track_id(key, value)
                    WHERE setting.key = 'race_assets'
                    UNION ALL
                    SELECT 'ACC' AS game, lower(track_id.key) AS track_name, track_id.value AS track_id
                    FROM app_settings setting
                    CROSS JOIN LATERAL jsonb_each_text(COALESCE(setting.value->'track_ids', '{}'::jsonb)) AS track_id(key, value)
                    WHERE setting.key = 'race_assets'
                )
                UPDATE races
                SET track_id = asset_track_ids.track_id
                FROM asset_track_ids
                WHERE races.track_id IS NULL
                  AND races.game = asset_track_ids.game
                  AND lower(races.track) = asset_track_ids.track_name
                """
            )
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_races_track_id ON races (track_id)"))
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
                    WHEN game IN ('LMU', 'Le Mans Ultimate') THEN 'LMU'
                    ELSE 'ACC'
                END
                WHERE game IS NULL OR game NOT IN ('ACC', 'AC', 'iRacing', 'LMU')
                """
            )
        )
        await conn.execute(text("ALTER TABLE races ADD COLUMN IF NOT EXISTS championship_id INTEGER"))
        await conn.execute(text("ALTER TABLE races ADD COLUMN IF NOT EXISTS championship_round INTEGER"))
        await conn.execute(text("ALTER TABLE races ADD COLUMN IF NOT EXISTS scoring_system VARCHAR(20)"))
        await conn.execute(text("ALTER TABLE races ADD COLUMN IF NOT EXISTS pole_bonus_enabled BOOLEAN"))
        await conn.execute(text("ALTER TABLE races ADD COLUMN IF NOT EXISTS is_team_event BOOLEAN DEFAULT FALSE"))
        await conn.execute(
            text(
                """
                UPDATE races
                SET scoring_system = COALESCE(races.scoring_system, championships.scoring_system, 'fia')
                FROM championships
                WHERE races.championship_id = championships.id
                  AND races.scoring_system IS NULL
                """
            )
        )
        await conn.execute(text("UPDATE races SET scoring_system = 'fia' WHERE scoring_system IS NULL OR scoring_system NOT IN ('fia', 'endurance', 'linear')"))
        await conn.execute(
            text(
                """
                UPDATE races
                SET pole_bonus_enabled = COALESCE(races.pole_bonus_enabled, championships.pole_bonus_enabled, FALSE)
                FROM championships
                WHERE races.championship_id = championships.id
                  AND races.pole_bonus_enabled IS NULL
                """
            )
        )
        await conn.execute(text("UPDATE races SET pole_bonus_enabled = FALSE WHERE pole_bonus_enabled IS NULL"))
        await conn.execute(text("UPDATE races SET is_team_event = FALSE WHERE is_team_event IS NULL"))
        await conn.execute(text("ALTER TABLE races ALTER COLUMN scoring_system SET DEFAULT 'fia'"))
        await conn.execute(text("ALTER TABLE races ALTER COLUMN pole_bonus_enabled SET DEFAULT FALSE"))
        await conn.execute(text("ALTER TABLE races ALTER COLUMN is_team_event SET DEFAULT FALSE"))
        await conn.execute(text("ALTER TABLE races ALTER COLUMN scoring_system SET NOT NULL"))
        await conn.execute(text("ALTER TABLE races ALTER COLUMN pole_bonus_enabled SET NOT NULL"))
        await conn.execute(text("ALTER TABLE races ALTER COLUMN is_team_event SET NOT NULL"))
        await conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'fk_races_championship_id'
                    ) THEN
                        ALTER TABLE races
                        ADD CONSTRAINT fk_races_championship_id
                        FOREIGN KEY (championship_id) REFERENCES championships(id)
                        ON DELETE CASCADE;
                    END IF;
                END $$;
                """
            )
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_races_championship_id ON races (championship_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_races_championship_round ON races (championship_id, championship_round)"))
        await conn.execute(text("UPDATE championships SET classes = '[]'::jsonb WHERE classes IS NULL OR jsonb_typeof(classes) <> 'array'"))
        await conn.execute(text("ALTER TABLE championships ALTER COLUMN classes SET DEFAULT '[]'::jsonb"))
        await conn.execute(text("ALTER TABLE championships ALTER COLUMN classes SET NOT NULL"))
        await conn.execute(text("UPDATE championships SET game = 'ACC' WHERE game IS NULL OR game NOT IN ('ACC', 'AC', 'iRacing', 'LMU')"))
        await conn.execute(text("ALTER TABLE championships ALTER COLUMN game SET DEFAULT 'ACC'"))
        await conn.execute(text("ALTER TABLE championships ALTER COLUMN game SET NOT NULL"))
        await conn.execute(text("UPDATE championships SET car_change_allowed = FALSE WHERE car_change_allowed IS NULL"))
        await conn.execute(text("UPDATE championships SET pole_bonus_enabled = FALSE WHERE pole_bonus_enabled IS NULL"))
        await conn.execute(text("ALTER TABLE championships ADD COLUMN IF NOT EXISTS is_team_event BOOLEAN DEFAULT FALSE"))
        await conn.execute(text("UPDATE championships SET is_team_event = FALSE WHERE is_team_event IS NULL"))
        await conn.execute(text("UPDATE championships SET is_published = FALSE WHERE is_published IS NULL"))
        await conn.execute(text("ALTER TABLE championships ALTER COLUMN car_change_allowed SET DEFAULT FALSE"))
        await conn.execute(text("ALTER TABLE championships ALTER COLUMN pole_bonus_enabled SET DEFAULT FALSE"))
        await conn.execute(text("ALTER TABLE championships ALTER COLUMN is_team_event SET DEFAULT FALSE"))
        await conn.execute(text("ALTER TABLE championships ALTER COLUMN is_published SET DEFAULT FALSE"))
        await conn.execute(text("ALTER TABLE championships ALTER COLUMN car_change_allowed SET NOT NULL"))
        await conn.execute(text("ALTER TABLE championships ALTER COLUMN pole_bonus_enabled SET NOT NULL"))
        await conn.execute(text("ALTER TABLE championships ALTER COLUMN is_team_event SET NOT NULL"))
        await conn.execute(text("ALTER TABLE championships ALTER COLUMN is_published SET NOT NULL"))
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS team_race_registrations (
                    id SERIAL PRIMARY KEY,
                    race_id INTEGER NOT NULL REFERENCES races(id) ON DELETE CASCADE,
                    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                    car_model VARCHAR(80) NOT NULL,
                    race_number INTEGER NOT NULL,
                    drivers JSONB NOT NULL DEFAULT '[]'::jsonb,
                    registered_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    registered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                )
                """
            )
        )
        await conn.execute(text("ALTER TABLE team_race_registrations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"))
        await conn.execute(text("UPDATE team_race_registrations SET drivers = '[]'::jsonb WHERE drivers IS NULL OR jsonb_typeof(drivers) <> 'array'"))
        await conn.execute(text("ALTER TABLE team_race_registrations ALTER COLUMN drivers SET DEFAULT '[]'::jsonb"))
        await conn.execute(text("ALTER TABLE team_race_registrations ALTER COLUMN drivers SET NOT NULL"))
        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_team_race_registration_race_team ON team_race_registrations (race_id, team_id)"))
        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_team_race_registration_race_number ON team_race_registrations (race_id, race_number)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_team_race_registrations_race_registered_at ON team_race_registrations (race_id, registered_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_team_race_registrations_team_registered_at ON team_race_registrations (team_id, registered_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_championships_published_registration ON championships (is_published, registration_start, registration_end)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_championships_published_dates ON championships (is_published, championship_start, championship_end)"))
        await conn.execute(text("ALTER TABLE race_registrations ADD COLUMN IF NOT EXISTS pilot_number INTEGER"))
        await conn.execute(
            text(
                """
                UPDATE race_registrations
                SET pilot_number = users.pilot_number
                FROM users
                WHERE race_registrations.user_id = users.id
                  AND race_registrations.pilot_number IS NULL
                """
            )
        )
        await conn.execute(text("ALTER TABLE race_registrations DROP CONSTRAINT IF EXISTS ck_race_registrations_pilot_number_range"))
        await conn.execute(text("UPDATE race_registrations SET pilot_number = 10000 + id WHERE pilot_number IS NOT NULL"))
        await conn.execute(
            text(
                """
                WITH ranked AS (
                    SELECT id, row_number() OVER (PARTITION BY race_id ORDER BY id) - 1 AS normalized_number
                    FROM race_registrations
                )
                UPDATE race_registrations
                SET pilot_number = ranked.normalized_number
                FROM ranked
                WHERE race_registrations.id = ranked.id
                """
            )
        )
        await conn.execute(text("ALTER TABLE race_registrations ADD CONSTRAINT ck_race_registrations_pilot_number_range CHECK (pilot_number >= 0 AND pilot_number <= 999)"))
        await conn.execute(text("ALTER TABLE race_registrations ALTER COLUMN pilot_number SET NOT NULL"))
        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_race_registration_race_pilot_number ON race_registrations (race_id, pilot_number)"))
        await conn.execute(text("ALTER TABLE championship_registrations ADD COLUMN IF NOT EXISTS pilot_number INTEGER"))
        await conn.execute(
            text(
                """
                UPDATE championship_registrations
                SET pilot_number = users.pilot_number
                FROM users
                WHERE championship_registrations.user_id = users.id
                  AND championship_registrations.pilot_number IS NULL
                """
            )
        )
        await conn.execute(text("ALTER TABLE championship_registrations DROP CONSTRAINT IF EXISTS ck_championship_registrations_pilot_number_range"))
        await conn.execute(text("UPDATE championship_registrations SET pilot_number = 10000 + id WHERE pilot_number IS NOT NULL"))
        await conn.execute(
            text(
                """
                WITH ranked AS (
                    SELECT id, row_number() OVER (PARTITION BY championship_id ORDER BY id) - 1 AS normalized_number
                    FROM championship_registrations
                )
                UPDATE championship_registrations
                SET pilot_number = ranked.normalized_number
                FROM ranked
                WHERE championship_registrations.id = ranked.id
                """
            )
        )
        await conn.execute(text("ALTER TABLE championship_registrations ADD CONSTRAINT ck_championship_registrations_pilot_number_range CHECK (pilot_number >= 0 AND pilot_number <= 999)"))
        await conn.execute(text("ALTER TABLE championship_registrations ALTER COLUMN pilot_number SET NOT NULL"))
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_championship_registration_pilot_number
                ON championship_registrations (championship_id, pilot_number)
                WHERE status <> 'rejected'
                """
            )
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_championship_registrations_status ON championship_registrations (championship_id, status)"))
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_championship_registration_pending_user
                ON championship_registrations (championship_id, user_id)
                """
            )
        )
