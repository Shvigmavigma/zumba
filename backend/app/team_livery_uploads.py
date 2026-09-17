import os
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from app.config import get_settings
from app.models import Team, TeamLiveryArchive


settings = get_settings()
TEAM_LIVERY_IMAGE_DIR = Path(settings.upload_dir) / "team-liveries"
TEAM_LIVERY_ARCHIVE_DIR = Path(settings.upload_dir) / "team-livery-archives"
ALLOWED_IMAGE_TYPES = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_LIVERY_IMAGES = 4
MAX_ARCHIVE_FILES = 5000
ARCHIVE_CHUNK_SIZE = 1024 * 1024


def livery_image_extension(file: UploadFile) -> str:
    extension = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if extension:
        return extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in ALLOWED_IMAGE_TYPES.values():
        return suffix
    raise HTTPException(status_code=415, detail="Only PNG, JPG, WEBP and GIF livery images are allowed")


def livery_image_url(team_id: int, filename: str) -> str:
    return f"/api/uploads/team-liveries/{team_id}/{filename}"


async def save_team_livery_image(file: UploadFile, team_id: int, max_mb: int) -> tuple[str, str]:
    extension = livery_image_extension(file)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded livery image is empty")
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Livery image is larger than {max_mb} MB")

    upload_dir = TEAM_LIVERY_IMAGE_DIR / str(team_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    (upload_dir / filename).write_bytes(data)
    original_filename = Path(file.filename or f"livery{extension}").name[:255]
    return livery_image_url(team_id, filename), original_filename


def _safe_upload_path(root: Path, relative_path: str) -> Path | None:
    try:
        target = (root / relative_path).resolve()
        target.relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    return target


def remove_team_livery_image_file(image_url: str | None) -> None:
    prefix = "/api/uploads/team-liveries/"
    if not image_url or not image_url.startswith(prefix):
        return
    target = _safe_upload_path(TEAM_LIVERY_IMAGE_DIR, image_url.removeprefix(prefix))
    if target is not None and target.is_file():
        target.unlink(missing_ok=True)


def team_livery_archive_path(team_id: int, filename: str) -> Path:
    return TEAM_LIVERY_ARCHIVE_DIR / str(team_id) / filename


def remove_team_livery_archive_file(team_id: int, filename: str | None) -> None:
    if not filename:
        return
    target = _safe_upload_path(TEAM_LIVERY_ARCHIVE_DIR / str(team_id), filename)
    if target is not None and target.is_file():
        target.unlink(missing_ok=True)


def _archive_member_name(filename: str | None) -> str:
    normalized = (filename or "").replace("\\", "/")
    parts = [part for part in PurePosixPath(normalized).parts if part not in {"", ".", ".."}]
    if parts and len(parts[0]) == 2 and parts[0][1] == ":":
        parts = parts[1:]
    if not parts:
        raise HTTPException(status_code=400, detail="Livery folder contains an invalid file name")
    return "/".join(parts)


def team_archive_folder_name(team: Team) -> str:
    return re.sub(r"[^\w-]+", "-", team.name.strip(), flags=re.UNICODE).strip("-_") or f"team-{team.id}"


def team_archive_filename(team: Team) -> str:
    date_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{date_key}_{team_archive_folder_name(team)}.zip"


async def create_team_livery_archive(files: list[UploadFile], team: Team, max_mb: int) -> tuple[str, int, Path]:
    if not files:
        raise HTTPException(status_code=400, detail="Choose a livery folder")
    if len(files) > MAX_ARCHIVE_FILES:
        raise HTTPException(status_code=413, detail=f"A livery folder can contain at most {MAX_ARCHIVE_FILES} files")

    filename = team_archive_filename(team)
    target_dir = TEAM_LIVERY_ARCHIVE_DIR / str(team.id)
    target_dir.mkdir(parents=True, exist_ok=True)
    temporary_path = target_dir / f".{uuid4().hex}.zip"
    total_bytes = 0
    names: set[str] = set()

    try:
        with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            for file in files:
                member_name = _archive_member_name(file.filename)
                if member_name in names:
                    raise HTTPException(status_code=400, detail="Livery folder contains duplicate file names")
                names.add(member_name)
                await file.seek(0)
                with archive.open(member_name, "w", force_zip64=True) as entry:
                    while True:
                        chunk = await file.read(ARCHIVE_CHUNK_SIZE)
                        if not chunk:
                            break
                        total_bytes += len(chunk)
                        if total_bytes > max_mb * 1024 * 1024:
                            raise HTTPException(status_code=413, detail=f"Livery archive is larger than {max_mb} MB")
                        entry.write(chunk)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return filename, total_bytes, temporary_path


def _remove_temporary_file(path: str) -> None:
    Path(path).unlink(missing_ok=True)


async def create_team_livery_archives_export(session: AsyncSession) -> FileResponse:
    rows = (
        await session.execute(
            select(TeamLiveryArchive, Team)
            .join(Team, Team.id == TeamLiveryArchive.team_id)
            .order_by(Team.abbreviation.asc(), Team.id.asc())
        )
    ).all()
    existing = [
        (archive, team, team_livery_archive_path(team.id, archive.archive_filename))
        for archive, team in rows
        if team_livery_archive_path(team.id, archive.archive_filename).is_file()
    ]
    if not existing:
        raise HTTPException(status_code=404, detail="No team livery archives are available")

    descriptor, path = tempfile.mkstemp(prefix="bmrl-team-liveries-", suffix=".zip")
    os.close(descriptor)
    try:
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as export:
            for archive, team, source in existing:
                export.write(source, arcname=f"{team_archive_folder_name(team)}/{archive.archive_filename}")
    except Exception:
        _remove_temporary_file(path)
        raise

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return FileResponse(
        path,
        media_type="application/zip",
        filename=f"bmrl-team-liveries-{timestamp}.zip",
        background=BackgroundTask(_remove_temporary_file, path),
    )
