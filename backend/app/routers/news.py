from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.deps import require_news_editor
from app.models import NewsItem, User
from app.rate_limit import limiter
from app.schemas import NewsItemRead, NewsItemUpdate


router = APIRouter()
settings = get_settings()
NEWS_UPLOAD_DIR = Path(settings.upload_dir) / "news"
ALLOWED_IMAGE_TYPES = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def invalidate_news_cache() -> None:
    return None


def ensure_news_upload_dir() -> None:
    NEWS_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def news_file_url(path: Path) -> str:
    return f"/api/uploads/news/{path.name}"


def delete_news_file(image_url: str) -> None:
    prefix = "/api/uploads/news/"
    if not image_url.startswith(prefix):
        return
    path = NEWS_UPLOAD_DIR / Path(image_url.removeprefix(prefix)).name
    if path.exists() and path.is_file():
        path.unlink()


def uploaded_extension(file: UploadFile) -> str:
    extension = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if extension:
        return extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in ALLOWED_IMAGE_TYPES.values():
        return suffix
    raise HTTPException(status_code=415, detail="Only PNG, JPG, WEBP and GIF images are allowed")


@router.get("", response_model=list[NewsItemRead])
@limiter.limit("1200/minute")
async def list_news(request: Request, session: AsyncSession = Depends(get_session)):
    items = (
        await session.scalars(
            select(NewsItem)
            .where(NewsItem.is_published.is_(True))
            .order_by(desc(NewsItem.created_at))
            .limit(24)
        )
    ).all()
    return items


@router.get("/manage", response_model=list[NewsItemRead])
@limiter.limit("120/minute")
async def list_news_for_manage(
    request: Request,
    user: User = Depends(require_news_editor),
    session: AsyncSession = Depends(get_session),
):
    return (
        await session.scalars(
            select(NewsItem)
            .order_by(desc(NewsItem.created_at))
            .limit(100)
        )
    ).all()


@router.post("", response_model=NewsItemRead)
@limiter.limit("20/minute")
async def create_news(
    request: Request,
    title: str = Form(..., min_length=1, max_length=120),
    body: str = Form(..., min_length=1, max_length=1000),
    is_published: bool = Form(True),
    file: UploadFile = File(...),
    user: User = Depends(require_news_editor),
    session: AsyncSession = Depends(get_session),
):
    extension = uploaded_extension(file)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(data) > settings.max_banner_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File is larger than {settings.max_banner_upload_mb} MB")

    ensure_news_upload_dir()
    path = NEWS_UPLOAD_DIR / f"news-{uuid4().hex}{extension}"
    path.write_bytes(data)

    item = NewsItem(
        title=title.strip(),
        body=body.strip(),
        image_url=news_file_url(path),
        is_published=is_published,
        created_by=user.id,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    invalidate_news_cache()
    return item


@router.patch("/{news_id}", response_model=NewsItemRead)
@limiter.limit("30/minute")
async def update_news(
    news_id: int,
    request: Request,
    payload: NewsItemUpdate,
    user: User = Depends(require_news_editor),
    session: AsyncSession = Depends(get_session),
):
    item = await session.get(NewsItem, news_id)
    if item is None:
        raise HTTPException(status_code=404, detail="News item not found")
    update = payload.model_dump(exclude_unset=True)
    for field, value in update.items():
        setattr(item, field, value.strip() if isinstance(value, str) else value)
    await session.commit()
    await session.refresh(item)
    invalidate_news_cache()
    return item


@router.delete("/{news_id}", status_code=204)
@limiter.limit("20/minute")
async def delete_news(
    news_id: int,
    request: Request,
    user: User = Depends(require_news_editor),
    session: AsyncSession = Depends(get_session),
):
    item = await session.get(NewsItem, news_id)
    if item is None:
        raise HTTPException(status_code=404, detail="News item not found")
    delete_news_file(item.image_url)
    await session.delete(item)
    await session.commit()
    invalidate_news_cache()
    return None
