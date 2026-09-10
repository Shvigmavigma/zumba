from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.deps import require_moder_plus, require_system_admin
from app.models import AuditLog, User
from app.rate_limit import limiter
from app.schemas import AdminDangerDeleteRequest, AuditLogRead
from app.security import verify_password


router = APIRouter()


def ensure_danger_request(payload: AdminDangerDeleteRequest, expected_confirmation: str) -> None:
    if payload.confirmation.strip() != expected_confirmation or payload.confirmation_repeat.strip() != expected_confirmation:
        raise HTTPException(status_code=400, detail="Confirmation phrase is invalid")
    danger_hash = get_settings().admin_danger_password_hash.strip()
    if not danger_hash:
        raise HTTPException(status_code=503, detail="Danger password is not configured")
    try:
        password_matches = verify_password(payload.password, danger_hash)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Danger password hash is invalid") from exc
    if not password_matches:
        raise HTTPException(status_code=403, detail="Danger password is invalid")


@router.get("", response_model=list[AuditLogRead])
@limiter.limit("120/minute")
async def list_audit_log(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(AuditLog, User.login.label("actor_login"))
            .outerjoin(User, User.id == AuditLog.actor_id)
            .order_by(desc(AuditLog.created_at), desc(AuditLog.id))
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return [
        AuditLogRead(
            id=log.id,
            created_at=log.created_at,
            actor_id=log.actor_id,
            actor_login=actor_login,
            actor_role=log.actor_role,
            method=log.method,
            path=log.path,
            status_code=log.status_code,
            action=log.action,
            details=log.details or {},
        )
        for log, actor_login in rows
    ]


@router.post("/clear")
@limiter.limit("3/minute")
async def clear_audit_log(
    request: Request,
    payload: AdminDangerDeleteRequest,
    _: User = Depends(require_system_admin),
    session: AsyncSession = Depends(get_session),
):
    ensure_danger_request(payload, "CLEAR AUDIT LOGS")
    result = await session.execute(delete(AuditLog))
    await session.commit()
    return {"deleted": result.rowcount or 0}
