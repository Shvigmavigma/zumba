from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.config import get_settings


AVATAR_DAILY_LIMIT = 3
ALLOWED_IMAGE_TYPES = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

settings = get_settings()
AVATAR_UPLOAD_DIR = Path(settings.upload_dir) / "avatars"


def avatar_extension(file: UploadFile) -> str:
    extension = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if extension:
        return extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in ALLOWED_IMAGE_TYPES.values():
        return suffix
    raise HTTPException(status_code=415, detail="Only PNG, JPG, WEBP and GIF images are allowed")


def current_upload_day() -> datetime:
    return datetime.now(timezone.utc)


def same_utc_day(first: datetime | None, second: datetime) -> bool:
    if first is None:
        return False
    if first.tzinfo is None:
        first = first.replace(tzinfo=timezone.utc)
    return first.astimezone(timezone.utc).date() == second.date()


def ensure_avatar_upload_allowed(entity) -> None:
    now = current_upload_day()
    if not same_utc_day(getattr(entity, "avatar_upload_window_start", None), now):
        entity.avatar_upload_count = 0
        entity.avatar_upload_window_start = now
    if int(getattr(entity, "avatar_upload_count", 0) or 0) >= AVATAR_DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="Avatar can be changed only 3 times per day")


def mark_avatar_uploaded(entity) -> None:
    entity.avatar_upload_count = int(getattr(entity, "avatar_upload_count", 0) or 0) + 1
    entity.avatar_upload_window_start = current_upload_day()


async def save_avatar_file(file: UploadFile, owner_kind: str, owner_id: int, max_mb: int) -> str:
    extension = avatar_extension(file)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File is larger than {max_mb} MB")

    upload_dir = AVATAR_UPLOAD_DIR / owner_kind
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / f"{owner_id}-{uuid4().hex}{extension}"
    path.write_bytes(data)
    return f"/api/uploads/avatars/{owner_kind}/{path.name}"


def remove_avatar_file(image_url: str | None) -> None:
    if not image_url or not image_url.startswith("/api/uploads/avatars/"):
        return
    relative = image_url.removeprefix("/api/uploads/")
    try:
        root = Path(settings.upload_dir).resolve()
        target = (root / relative).resolve()
        target.relative_to(root)
    except (OSError, ValueError):
        return
    if target.is_file():
        target.unlink(missing_ok=True)
