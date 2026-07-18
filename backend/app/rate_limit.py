from fastapi import Request
from slowapi import Limiter

from app.config import get_settings
from app.security import decode_access_token


def request_limit_key() -> str:
    return "all-users"


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
