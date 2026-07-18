from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Race, RaceStatus, Role, User, UserStatus
from app.rate_limit import limiter
from app.schemas import DashboardStats


router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
@limiter.limit("3/minute")
async def stats(request: Request, session: AsyncSession = Depends(get_session)):
    pilots = await session.scalar(select(func.count()).select_from(User).where(User.status == UserStatus.active))
    completed = await session.scalar(select(func.count()).select_from(Race).where(Race.status == RaceStatus.finished))
    open_races = await session.scalar(select(func.count()).select_from(Race).where(Race.status == RaceStatus.registration_open))
    staff = await session.scalar(select(func.count()).select_from(User).where(User.role.in_([Role.admin, Role.moder, Role.marshall, Role.smm])))
    return DashboardStats(pilots=pilots or 0, completed_races=completed or 0, open_races=open_races or 0, staff=staff or 0)

