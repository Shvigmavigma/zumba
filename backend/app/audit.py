import logging
from dataclasses import dataclass

from fastapi import Request

from app.db import SessionLocal
from app.models import AuditLog, Role
from app.security import decode_access_token


logger = logging.getLogger(__name__)
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SKIP_PREFIXES = ("/api/auth", "/api/audit", "/api/uploads")


@dataclass(frozen=True)
class AuditActor:
    user_id: int
    role: str


def actor_from_request(request: Request) -> AuditActor | None:
    if request.method.upper() not in MUTATING_METHODS:
        return None
    path = request.url.path
    if not path.startswith("/api/") or path.startswith(SKIP_PREFIXES):
        return None
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    try:
        payload = decode_access_token(header.split(" ", 1)[1].strip())
        role = str(payload.get("role") or "")
        if role == Role.pilot.value:
            return None
        return AuditActor(user_id=int(payload["sub"]), role=role)
    except Exception:
        return None


async def request_audit_details(request: Request) -> dict:
    details = {"query": request.url.query} if request.url.query else {}
    if "application/json" not in request.headers.get("content-type", "").lower():
        return details
    try:
        payload = await request.json()
    except Exception:
        return details
    if isinstance(payload, dict):
        details["fields"] = sorted(str(key) for key in payload if str(key).lower() not in {"password", "password_hash", "token", "access_token"})
    return details


async def write_audit_log_with_details(request: Request, response_status: int, actor: AuditActor, details: dict) -> None:
    try:
        async with SessionLocal() as session:
            session.add(
                AuditLog(
                    actor_id=actor.user_id,
                    actor_role=actor.role,
                    method=request.method.upper(),
                    path=request.url.path[:255],
                    status_code=response_status,
                    action=f"{request.method.upper()} {request.url.path}"[:140],
                    details=details,
                )
            )
            await session.commit()
    except Exception:
        logger.exception("Could not write audit log")
