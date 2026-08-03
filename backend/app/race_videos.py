from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.config import get_settings


ALLOWED_VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
    "video/x-matroska": ".mkv",
}

settings = get_settings()
RACE_VIDEO_UPLOAD_DIR = Path(settings.upload_dir) / "race-videos"


def video_extension(file: UploadFile) -> str:
    extension = ALLOWED_VIDEO_TYPES.get(file.content_type or "")
    if extension:
        return extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in ALLOWED_VIDEO_TYPES.values():
        return suffix
    raise HTTPException(status_code=415, detail="Only MP4, MOV, WEBM and MKV videos are allowed")


async def save_race_video_file(file: UploadFile, race_id: int) -> str:
    extension = video_extension(file)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(data) > settings.max_race_video_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File is larger than {settings.max_race_video_upload_mb} MB")

    RACE_VIDEO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = RACE_VIDEO_UPLOAD_DIR / f"{race_id}-{uuid4().hex}{extension}"
    path.write_bytes(data)
    return f"/api/uploads/race-videos/{path.name}"


def remove_uploaded_file(file_url: str | None, allowed_prefix: str = "/api/uploads/") -> None:
    if not file_url or not file_url.startswith(allowed_prefix):
        return
    relative = file_url.removeprefix("/api/uploads/")
    try:
        root = Path(settings.upload_dir).resolve()
        target = (root / relative).resolve()
        target.relative_to(root)
    except (OSError, ValueError):
        return
    if target.is_file():
        target.unlink(missing_ok=True)


def remove_race_video_file(video_url: str | None) -> None:
    remove_uploaded_file(video_url, "/api/uploads/race-videos/")
