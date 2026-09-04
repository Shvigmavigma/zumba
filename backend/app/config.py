from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BMRL Race Control"
    app_domain: str = "xskynet.ru"
    public_base_url: str = "http://xskynet.ru"
    cors_origins: str = "http://xskynet.ru"

    database_url: str = "postgresql+asyncpg://bmrl:bmrl@postgres:5432/bmrl"
    db_pool_size: int = 20
    db_max_overflow: int = 40
    auto_create_tables: bool = True

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    admin_login: str = "admin"
    admin_email: str = "admin@example.com"
    admin_password: str = "admin"
    admin_danger_password_hash: str = ""

    rate_limit_default: str = "3/minute"
    rate_limit_storage_uri: str | None = None
    steam_openid_url: str = "https://steamcommunity.com/openid/login"
    upload_dir: str = "/app/uploads"
    max_banner_upload_mb: int = 20
    max_logo_upload_mb: int = 5
    max_user_avatar_upload_mb: int = 5
    max_team_avatar_upload_mb: int = 30
    max_race_video_upload_mb: int = 300
    twitch_channel_login: str = "bmrlracing"
    twitch_client_id: str = ""
    twitch_client_secret: str = ""
    twitch_status_cache_seconds: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
