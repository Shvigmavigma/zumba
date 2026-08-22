from time import time

from fastapi import Request
from redis import Redis
from slowapi import Limiter

from app.config import get_settings
from app.security import decode_access_token


TOKEN_KEY_CACHE_TTL_SECONDS = 60
MAX_TOKEN_KEY_CACHE_SIZE = 4096

_token_key_cache: dict[str, tuple[float, str]] = {}


def ip_limit_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return f"ip:{forwarded_for.split(',', 1)[0].strip()}"
    if request.client:
        return f"ip:{request.client.host}"
    return "ip:anonymous"


def cached_token_limit_key(token: str) -> str | None:
    now = time()
    cached = _token_key_cache.get(token)
    if cached is not None:
        expires_at, key = cached
        if expires_at > now:
            return key
        _token_key_cache.pop(token, None)

    try:
        payload = decode_access_token(token)
    except Exception:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    if len(_token_key_cache) >= MAX_TOKEN_KEY_CACHE_SIZE:
        expired_tokens = [cached_token for cached_token, (expires_at, _) in _token_key_cache.items() if expires_at <= now]
        for cached_token in expired_tokens:
            _token_key_cache.pop(cached_token, None)
        if len(_token_key_cache) >= MAX_TOKEN_KEY_CACHE_SIZE:
            _token_key_cache.clear()

    expires_at = now + TOKEN_KEY_CACHE_TTL_SECONDS
    token_exp = payload.get("exp")
    if isinstance(token_exp, (int, float)):
        expires_at = min(expires_at, float(token_exp))

    key = f"user:{user_id}"
    _token_key_cache[token] = (expires_at, key)
    return key


def request_limit_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token_key = cached_token_limit_key(auth.split(" ", 1)[1])
        if token_key is not None:
            return token_key
    return ip_limit_key(request)


def is_admin_request(request: Request) -> bool:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return False
    token = auth.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except Exception:
        return False
    return payload.get("role") == "admin"


settings = get_settings()
DEFAULT_REQUESTS_PER_USER_PER_MINUTE = 1200
RUNTIME_LIMIT_REDIS_KEY = "bmrl:settings:requests_per_user_per_minute"
_requests_per_user_per_minute = DEFAULT_REQUESTS_PER_USER_PER_MINUTE
_runtime_limit_store: Redis | None = None


def _get_runtime_limit_store() -> Redis | None:
    global _runtime_limit_store
    if _runtime_limit_store is not None:
        return _runtime_limit_store
    uri = settings.rate_limit_storage_uri or ""
    if not uri.startswith(("redis://", "rediss://")):
        return None
    try:
        _runtime_limit_store = Redis.from_url(
            uri,
            decode_responses=True,
            socket_connect_timeout=0.2,
            socket_timeout=0.2,
        )
    except Exception:
        return None
    return _runtime_limit_store


def set_requests_per_user_per_minute(value: int) -> int:
    global _requests_per_user_per_minute
    _requests_per_user_per_minute = max(1, min(10000, int(value)))
    store = _get_runtime_limit_store()
    if store is not None:
        try:
            store.set(RUNTIME_LIMIT_REDIS_KEY, _requests_per_user_per_minute)
        except Exception:
            # The database remains the source of truth; local state keeps the
            # current worker functional if Redis is temporarily unavailable.
            pass
    return _requests_per_user_per_minute


def set_rate_limit_per_minute(value: int) -> int:
    """Backward-compatible alias for older callers."""
    return set_requests_per_user_per_minute(value)


def configured_application_limit() -> str:
    value = _requests_per_user_per_minute
    store = _get_runtime_limit_store()
    if store is not None:
        try:
            value = max(1, min(10000, int(store.get(RUNTIME_LIMIT_REDIS_KEY) or value)))
        except Exception:
            pass
    return f"{value}/minute"


limiter = Limiter(
    key_func=request_limit_key,
    application_limits=[configured_application_limit],
    headers_enabled=False,
    storage_uri=settings.rate_limit_storage_uri,
)
