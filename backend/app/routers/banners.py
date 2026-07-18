from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_banner_editor
from app.models import Banner, BannerPosition, User
from app.rate_limit import limiter
from app.schemas import BannerRead, BannerUpdate


router = APIRouter()


@router.get("", response_model=list[BannerRead])
@limiter.limit("3/minute")
async def list_banners(request: Request, session: AsyncSession = Depends(get_session)):
    return (await session.scalars(select(Banner).order_by(Banner.position))).all()


@router.put("/{position}", response_model=BannerRead)
@limiter.limit("3/minute")
async def update_banner(
    position: BannerPosition,
    request: Request,
    payload: BannerUpdate,
    user: User = Depends(require_banner_editor),
    session: AsyncSession = Depends(get_session),
):
    banner = await session.scalar(select(Banner).where(Banner.position == position))
    if banner is None:
        raise HTTPException(status_code=404, detail="Banner not found")
    banner.image_url = payload.image_url
    banner.link_url = payload.link_url
    banner.updated_by = user.id
    await session.commit()
    await session.refresh(banner)
    return banner
