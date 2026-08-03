from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_admin, require_pilot_plus
from app.rate_limit import limiter
from app.race_assets import get_race_assets, save_race_assets
from app.schemas import RaceAssetsConfig


router = APIRouter()


@router.get("", response_model=RaceAssetsConfig)
@limiter.limit("600/minute")
async def read_race_assets(
    request: Request,
    _: object = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    return await get_race_assets(session)


@router.patch("", response_model=RaceAssetsConfig)
@limiter.limit("20/minute")
async def update_race_assets(
    payload: RaceAssetsConfig,
    request: Request,
    _: object = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await save_race_assets(session, payload)
