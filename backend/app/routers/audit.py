from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_moder_plus
from app.models import AuditLog, User
from app.rate_limit import limiter
from app.schemas import AuditLogRead


router = APIRouter()


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
