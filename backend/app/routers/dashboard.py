from fastapi import APIRouter, Depends, Request
from time import monotonic

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Race, RaceStatus, Role, User, UserStatus
from app.rate_limit import limiter
from app.schemas import DashboardStats


router = APIRouter()
STATS_CACHE_TTL_SECONDS = 15
_stats_cache: tuple[float, DashboardStats] | None = None


@router.get("/stats", response_model=DashboardStats)
@limiter.limit("1200/minute")
async def stats(request: Request, session: AsyncSession = Depends(get_session)):
    global _stats_cache
    now = monotonic()
    if _stats_cache is not None and now < _stats_cache[0]:
        return _stats_cache[1]

    pilots = await session.scalar(select(func.count()).select_from(User).where(User.status == UserStatus.active))
    completed = await session.scalar(select(func.count()).select_from(Race).where(Race.status == RaceStatus.finished))
    open_races = await session.scalar(select(func.count()).select_from(Race).where(Race.status == RaceStatus.registration_open))
    staff = await session.scalar(select(func.count()).select_from(User).where(User.role.in_([Role.admin, Role.moder, Role.marshall, Role.smm])))
    cached = DashboardStats(pilots=pilots or 0, completed_races=completed or 0, open_races=open_races or 0, staff=staff or 0)
    _stats_cache = (now + STATS_CACHE_TTL_SECONDS, cached)
    return cached

