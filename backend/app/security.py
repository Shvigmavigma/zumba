from datetime import datetime, timedelta, timezone
import secrets
from typing import Any

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext
from redis import Redis

from app.config import get_settings
from app.models import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_STEAM_REGISTRATION_TTL_SECONDS = 15 * 60
_steam_registration_store: Redis | None = None


def _steam_registration_redis() -> Redis:
    global _steam_registration_store
    if _steam_registration_store is None:
        uri = get_settings().rate_limit_storage_uri or ""
        if not uri.startswith(("redis://", "rediss://")):
            raise HTTPException(status_code=503, detail="Steam registration storage is unavailable")
        _steam_registration_store = Redis.from_url(
            uri,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
    try:
        _steam_registration_store.ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Steam registration storage is unavailable") from exc
    return _steam_registration_store


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user: User) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user.id),
        "login": user.login,
        "role": user.role.value,
        "exp": expires,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_steam_registration_token(steam_id: str) -> str:
    # Use an opaque, one-time token.  A JWT containing the Steam ID would be
    # readable by the registering browser even when it is signed correctly.
    token = secrets.token_urlsafe(32)
    store = _steam_registration_redis()
    try:
        store.setex(f"bmrl:steam-registration:{token}", _STEAM_REGISTRATION_TTL_SECONDS, steam_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Steam registration storage is unavailable") from exc
    return token


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def decode_steam_registration_token(token: str) -> str:
    if not token or len(token) > 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Steam authentication is required")
    store = _steam_registration_redis()
    try:
        steam_id = store.getdel(f"bmrl:steam-registration:{token}")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Steam registration storage is unavailable") from exc
    if not isinstance(steam_id, str) or not steam_id.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Steam authentication is required")
    return steam_id
