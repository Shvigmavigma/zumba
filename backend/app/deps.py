from datetime import datetime, timezone
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import Role, User, UserStatus
from app.security import decode_access_token


bearer = HTTPBearer(auto_error=False)

PILOT_PLUS = {Role.admin, Role.moder, Role.marshall, Role.smm, Role.pilot}
MODER_PLUS = {Role.admin, Role.moder}
MARSHALL_PLUS = {Role.admin, Role.moder, Role.marshall}
BANNER_EDITORS = {Role.admin, Role.moder, Role.smm}


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def clear_expired_timeout(user: User, now: datetime | None = None) -> bool:
    if user.status != UserStatus.timeout or user.timeout_end is None:
        return False
    current_time = now or datetime.now(timezone.utc)
    if as_utc(user.timeout_end) > current_time:
        return False
    user.status = UserStatus.active
    user.timeout_start = None
    user.timeout_end = None
    return True


async def resolve_user_from_token(
    credentials: HTTPAuthorizationCredentials | None,
    session: AsyncSession,
) -> User | None:
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    user_id = int(payload["sub"])
    user = await session.get(User, user_id)
    if user is None:
        return None
    if clear_expired_timeout(user):
        await session.commit()
        await session.refresh(user)
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    return await resolve_user_from_token(credentials, session)


async def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def require_active(user: User) -> None:
    if user.status != UserStatus.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Account status is {user.status.value}")


def is_system_admin(user: User) -> bool:
    return user.login == get_settings().admin_login


def ensure_not_system_admin(user: User) -> None:
    if is_system_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The system administrator is protected")


def require_roles(allowed: set[Role]) -> Callable[[User], User]:
    async def dependency(user: User = Depends(get_current_user)) -> User:
        require_active(user)
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency


require_admin = require_roles({Role.admin})


async def require_system_admin(user: User = Depends(get_current_user)) -> User:
    require_active(user)
    if user.role != Role.admin or not is_system_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System administrator access required")
    return user


require_pilot_plus = require_roles(PILOT_PLUS)
require_moder_plus = require_roles(MODER_PLUS)
require_marshall_plus = require_roles(MARSHALL_PLUS)
require_banner_editor = require_roles(BANNER_EDITORS)
require_news_editor = require_roles(BANNER_EDITORS)
