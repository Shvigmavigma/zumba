from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_admin, require_moder_plus, require_pilot_plus
from app.models import Role, User, UserStatus
from app.rate_limit import limiter
from app.schemas import RoleUpdate, TimeoutRequest, UserPrivate, UserPublic, UserUpdate


router = APIRouter()


@router.get("/pilots", response_model=list[UserPublic])
@limiter.limit("3/minute")
async def list_pilots(
    request: Request,
    search: str | None = None,
    country: str | None = None,
    offset: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    limit = min(limit, 100)
    stmt = select(User).where(User.status == UserStatus.active)
    if country:
        stmt = stmt.where(User.country == country)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(User.login.ilike(like), User.nickname.ilike(like), User.first_name.ilike(like), User.last_name.ilike(like)))
    stmt = stmt.order_by(User.sr.desc(), User.pilot_number.asc()).offset(offset).limit(limit)
    return (await session.scalars(stmt)).all()


@router.get("/moderation/pending", response_model=list[UserPrivate])
@limiter.limit("3/minute")
async def pending_users(request: Request, _: User = Depends(require_moder_plus), session: AsyncSession = Depends(get_session)):
    return (
        await session.scalars(
            select(User)
            .where(or_(User.status == UserStatus.unapproved, User.pending_profile_changes.is_not(None)))
            .order_by(User.created_at)
        )
    ).all()


@router.get("/admin", response_model=list[UserPrivate])
@limiter.limit("3/minute")
async def admin_user_list(
    request: Request,
    _: User = Depends(require_admin),
    offset: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
):
    return (await session.scalars(select(User).order_by(User.created_at.desc()).offset(offset).limit(min(limit, 200)))).all()


@router.get("/{user_id}", response_model=UserPublic)
@limiter.limit("3/minute")
async def get_user(user_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/me", response_model=UserPrivate)
@limiter.limit("3/minute")
async def update_me(
    request: Request,
    payload: UserUpdate,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    data = payload.model_dump(exclude_unset=True)
    required_fields = {"email", "first_name", "last_name", "nickname", "avatar_color"}
    if any(field in data and data[field] is None for field in required_fields):
        raise HTTPException(status_code=400, detail="Required profile fields cannot be null")
    if "email" in data:
        existing_email = await session.scalar(select(User).where(User.email == str(data["email"]), User.id != user.id))
        if existing_email is not None:
            raise HTTPException(status_code=409, detail="Email already exists")
    if user.role == Role.admin:
        for field, value in data.items():
            setattr(user, field, value)
    elif data:
        user.pending_profile_changes = data
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/{user_id}/approve", response_model=UserPrivate)
@limiter.limit("3/minute")
async def approve_user(user_id: int, request: Request, _: User = Depends(require_moder_plus), session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.pending_profile_changes:
        if "email" in user.pending_profile_changes:
            existing_email = await session.scalar(
                select(User).where(User.email == str(user.pending_profile_changes["email"]), User.id != user.id)
            )
            if existing_email is not None:
                raise HTTPException(status_code=409, detail="Email already exists")
        for field, value in user.pending_profile_changes.items():
            setattr(user, field, value)
        user.pending_profile_changes = None
    if user.status == UserStatus.unapproved:
        user.status = UserStatus.active
    await session.commit()
    await session.refresh(user)
    return user


@router.delete("/{user_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/minute")
async def reject_user(user_id: int, request: Request, _: User = Depends(require_moder_plus), session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.status == UserStatus.unapproved:
        await session.delete(user)
    elif user.pending_profile_changes:
        user.pending_profile_changes = None
    else:
        raise HTTPException(status_code=400, detail="No registration or profile change to reject")
    await session.commit()


@router.patch("/{user_id}/role", response_model=UserPrivate)
@limiter.limit("3/minute")
async def update_role(
    user_id: int,
    request: Request,
    payload: RoleUpdate,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = payload.role
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/{user_id}/ban", response_model=UserPrivate)
@limiter.limit("3/minute")
async def ban_user(user_id: int, request: Request, _: User = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == Role.admin:
        raise HTTPException(status_code=403, detail="Admins cannot be banned")
    user.status = UserStatus.banned
    user.ban_end = None
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/{user_id}/unban", response_model=UserPrivate)
@limiter.limit("3/minute")
async def unban_user(user_id: int, request: Request, _: User = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = UserStatus.active
    user.ban_end = None
    user.timeout_start = None
    user.timeout_end = None
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/{user_id}/timeout", response_model=UserPrivate)
@limiter.limit("3/minute")
async def timeout_user(
    user_id: int,
    request: Request,
    payload: TimeoutRequest,
    _: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    if payload.timeout_end <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Timeout end must be in the future")
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = UserStatus.timeout
    user.timeout_start = datetime.now(timezone.utc)
    user.timeout_end = payload.timeout_end
    await session.commit()
    await session.refresh(user)
    return user
