from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.deps import require_banner_editor
from app.models import Banner, BannerPosition, User
from app.rate_limit import limiter
from app.schemas import BannerFileRead, BannerRead, BannerUpdate


router = APIRouter()
settings = get_settings()
BANNER_UPLOAD_DIR = Path(settings.upload_dir) / "banners"
BANNER_CACHE_TTL_SECONDS = 30
_banners_cache: tuple[float, list[BannerRead]] | None = None
ALLOWED_MEDIA_TYPES = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
    "video/x-matroska": ".mkv",
}


def invalidate_banner_cache() -> None:
    global _banners_cache
    _banners_cache = None


def ensure_banner_upload_dir() -> None:
    BANNER_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def banner_file_url(path: Path) -> str:
    return f"/api/uploads/banners/{path.name}"


def file_read(path: Path) -> BannerFileRead:
    stat = path.stat()
    return BannerFileRead(
        name=path.name,
        url=banner_file_url(path),
        size=stat.st_size,
        updated_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
    )


def uploaded_extension(file: UploadFile) -> str:
    extension = ALLOWED_MEDIA_TYPES.get(file.content_type or "")
    if extension:
        return extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in ALLOWED_MEDIA_TYPES.values():
        return suffix
    raise HTTPException(status_code=415, detail="Only PNG, JPG, WEBP, GIF, MP4, MOV, WEBM and MKV files are allowed")


@router.get("", response_model=list[BannerRead])
@limiter.limit("1200/minute")
async def list_banners(request: Request, session: AsyncSession = Depends(get_session)):
    global _banners_cache
    now = monotonic()
    if _banners_cache is not None and now < _banners_cache[0]:
        return _banners_cache[1]

    banners = [BannerRead.model_validate(banner) for banner in (await session.scalars(select(Banner).order_by(Banner.position))).all()]
    _banners_cache = (now + BANNER_CACHE_TTL_SECONDS, banners)
    return banners


@router.get("/files", response_model=list[BannerFileRead])
@limiter.limit("60/minute")
async def list_banner_files(
    request: Request,
    user: User = Depends(require_banner_editor),
):
    ensure_banner_upload_dir()
    return sorted(
        (file_read(path) for path in BANNER_UPLOAD_DIR.iterdir() if path.is_file()),
        key=lambda item: item.updated_at,
        reverse=True,
    )


@router.post("/{position}/upload", response_model=BannerRead)
@limiter.limit("10/minute")
async def upload_banner(
    position: BannerPosition,
    request: Request,
    file: UploadFile = File(...),
    link_url: str = Form("#"),
    user: User = Depends(require_banner_editor),
    session: AsyncSession = Depends(get_session),
):
    banner = await session.scalar(select(Banner).where(Banner.position == position))
    if banner is None:
        raise HTTPException(status_code=404, detail="Banner not found")

    extension = uploaded_extension(file)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(data) > settings.max_banner_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File is larger than {settings.max_banner_upload_mb} MB")

    ensure_banner_upload_dir()
    path = BANNER_UPLOAD_DIR / f"{position.value}-{uuid4().hex}{extension}"
    path.write_bytes(data)

    banner.image_url = banner_file_url(path)
    banner.link_url = link_url or "#"
    banner.updated_by = user.id
    await session.commit()
    await session.refresh(banner)
    invalidate_banner_cache()
    return banner


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
    invalidate_banner_cache()
    return banner


@router.delete("/{position}", response_model=BannerRead)
@limiter.limit("10/minute")
async def clear_banner(
    position: BannerPosition,
    request: Request,
    user: User = Depends(require_banner_editor),
    session: AsyncSession = Depends(get_session),
):
    banner = await session.scalar(select(Banner).where(Banner.position == position))
    if banner is None:
        raise HTTPException(status_code=404, detail="Banner not found")
    banner.image_url = ""
    banner.link_url = "#"
    banner.updated_by = user.id
    await session.commit()
    await session.refresh(banner)
    invalidate_banner_cache()
    return banner
