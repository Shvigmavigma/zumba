from threading import Lock
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
DEFAULT_REQUESTS_PER_IP_PER_MINUTE = 1200
RUNTIME_LIMIT_REDIS_KEY = "bmrl:settings:requests_per_user_per_minute"
RUNTIME_IP_LIMIT_REDIS_KEY = "bmrl:settings:requests_per_ip_per_minute"
RATE_LIMIT_WINDOW_SECONDS = 60
_requests_per_user_per_minute = DEFAULT_REQUESTS_PER_USER_PER_MINUTE
_requests_per_ip_per_minute = DEFAULT_REQUESTS_PER_IP_PER_MINUTE
_runtime_limit_store: Redis | None = None
_memory_limit_buckets: dict[tuple[str, str, int, int], int] = {}
_memory_limit_lock = Lock()


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


def _clamp_limit(value: int) -> int:
    return max(1, min(10000, int(value)))


def set_request_limits(user_value: int, ip_value: int | None = None) -> tuple[int, int]:
    global _requests_per_user_per_minute, _requests_per_ip_per_minute
    _requests_per_user_per_minute = _clamp_limit(user_value)
    _requests_per_ip_per_minute = _clamp_limit(ip_value if ip_value is not None else user_value)
    store = _get_runtime_limit_store()
    if store is not None:
        try:
            store.mset(
                {
                    RUNTIME_LIMIT_REDIS_KEY: _requests_per_user_per_minute,
                    RUNTIME_IP_LIMIT_REDIS_KEY: _requests_per_ip_per_minute,
                }
            )
        except Exception:
            # The database remains the source of truth; local state keeps the
            # current worker functional if Redis is temporarily unavailable.
            pass
    return _requests_per_user_per_minute, _requests_per_ip_per_minute


def set_requests_per_user_per_minute(value: int) -> int:
    """Backward-compatible setter for the user limit."""
    set_request_limits(value, _requests_per_ip_per_minute)
    return _requests_per_user_per_minute


def set_requests_per_ip_per_minute(value: int) -> int:
    """Update only the IP limit while retaining the user limit."""
    set_request_limits(_requests_per_user_per_minute, value)
    return _requests_per_ip_per_minute


def set_rate_limit_per_minute(value: int) -> int:
    """Backward-compatible alias for older callers."""
    return set_requests_per_user_per_minute(value)


def configured_request_limits() -> tuple[int, int]:
    user_value = _requests_per_user_per_minute
    ip_value = _requests_per_ip_per_minute
    store = _get_runtime_limit_store()
    if store is not None:
        try:
            values = store.mget([RUNTIME_LIMIT_REDIS_KEY, RUNTIME_IP_LIMIT_REDIS_KEY])
            user_value = _clamp_limit(values[0] or user_value)
            ip_value = _clamp_limit(values[1] or ip_value)
        except Exception:
            pass
    return user_value, ip_value


def configured_application_limit() -> str:
    """Compatibility helper for integrations that still read the user limit."""
    return f"{configured_request_limits()[0]}/minute"


def _consume_limit(scope: str, identifier: str, limit: int) -> bool:
    window = int(time() // RATE_LIMIT_WINDOW_SECONDS)
    # Include the current limit so changing it starts a fresh bucket instead
    # of inheriting a counter collected under the previous value.
    key = f"bmrl:requests:{scope}:{identifier}:{window}:{limit}"
    store = _get_runtime_limit_store()
    if store is not None:
        try:
            pipe = store.pipeline(transaction=True)
            pipe.incr(key)
            pipe.expire(key, RATE_LIMIT_WINDOW_SECONDS + 1)
            count = int(pipe.execute()[0])
            return count <= limit
        except Exception:
            pass

    memory_key = (scope, identifier, window, limit)
    with _memory_limit_lock:
        _memory_limit_buckets[memory_key] = _memory_limit_buckets.get(memory_key, 0) + 1
        if len(_memory_limit_buckets) > 4096:
            current_window = window
            stale = [item for item in _memory_limit_buckets if item[2] < current_window - 1]
            for item in stale:
                _memory_limit_buckets.pop(item, None)
        return _memory_limit_buckets[memory_key] <= limit


def check_dynamic_rate_limit(request: Request) -> tuple[str, int] | None:
    """Apply the runtime user and IP limits to API requests.

    Static per-route SlowAPI limits remain a second safety layer; these limits
    are the values configurable from the admin panel and are shared through
    Redis between workers.
    """
    if request.method.upper() == "OPTIONS":
        return None
    path = request.url.path
    if not path.startswith("/api/") or path.startswith(("/api/uploads/", "/api/docs", "/api/openapi.json")):
        return None

    user_limit, ip_limit = configured_request_limits()
    auth = request.headers.get("authorization", "")
    user_key = None
    if auth.lower().startswith("bearer "):
        user_key = cached_token_limit_key(auth.split(" ", 1)[1].strip())
    if user_key is not None and not _consume_limit("user", user_key, user_limit):
        return "user", user_limit
    ip_key = ip_limit_key(request)
    if not _consume_limit("ip", ip_key, ip_limit):
        return "ip", ip_limit
    return None


limiter = Limiter(
    key_func=request_limit_key,
    # Runtime user/IP limits are enforced by check_dynamic_rate_limit. Keeping
    # them out of SlowAPI avoids a duplicate user counter and allows the IP key
    # to be enforced alongside the user key.
    application_limits=[],
    headers_enabled=False,
    storage_uri=settings.rate_limit_storage_uri,
)
