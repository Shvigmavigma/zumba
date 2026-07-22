from time import time

from fastapi import Request
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
limiter = Limiter(key_func=request_limit_key, headers_enabled=False, storage_uri=settings.rate_limit_storage_uri)
