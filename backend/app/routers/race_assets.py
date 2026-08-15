from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.deps import require_admin, require_moder_plus
from app.rate_limit import limiter
from app.race_assets import get_race_assets, save_race_assets
from app.schemas import AssetGameCode, RaceAssetsConfig


router = APIRouter()
settings = get_settings()
TRACK_IMAGE_UPLOAD_DIR = Path(settings.upload_dir) / "track-images"
ALLOWED_IMAGE_TYPES = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def uploaded_image_extension(file: UploadFile) -> str:
    extension = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if extension:
        return extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in ALLOWED_IMAGE_TYPES.values():
        return suffix
    raise HTTPException(status_code=415, detail="Only PNG, JPG, WEBP and GIF files are allowed")


def track_image_url(path: Path) -> str:
    return f"/api/uploads/track-images/{path.name}"


def remove_track_image_file(image_url: str | None) -> None:
    prefix = "/api/uploads/track-images/"
    if not image_url or not image_url.startswith(prefix):
        return
    try:
        root = TRACK_IMAGE_UPLOAD_DIR.resolve()
        target = (root / image_url.removeprefix(prefix)).resolve()
        target.relative_to(root)
    except (OSError, ValueError):
        return
    if target.is_file():
        target.unlink(missing_ok=True)


@router.get("", response_model=RaceAssetsConfig)
@limiter.limit("600/minute")
async def read_race_assets(
    request: Request,
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


@router.post("/track-image", response_model=RaceAssetsConfig)
@limiter.limit("30/minute")
async def upload_track_image(
    request: Request,
    game: AssetGameCode = Form(...),
    track: str = Form(...),
    file: UploadFile = File(...),
    _: object = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    config = await get_race_assets(session)
    game_config = config.games.get(game)
    track_name = track.strip()
    if not track_name:
        raise HTTPException(status_code=400, detail="Track is required")
    if game_config is None:
        raise HTTPException(status_code=404, detail="Game assets not found")
    existing_track = next((item for item in game_config.tracks if item.lower() == track_name.lower()), None)
    if existing_track:
        track_name = existing_track
    else:
        game_config.tracks = [*game_config.tracks, track_name]

    extension = uploaded_image_extension(file)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File is larger than 10 MB")

    TRACK_IMAGE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = TRACK_IMAGE_UPLOAD_DIR / f"{game.lower()}-{uuid4().hex}{extension}"
    path.write_bytes(data)

    previous = game_config.track_images.get(track_name)
    game_config.track_images = {**game_config.track_images, track_name: track_image_url(path)}
    if game == "ACC":
        config.tracks = list(game_config.tracks)
        config.track_images = dict(game_config.track_images)
        config.track_ids = dict(game_config.track_ids)
    saved = await save_race_assets(session, config)
    remove_track_image_file(previous)
    return saved


@router.delete("/track-image", response_model=RaceAssetsConfig)
@limiter.limit("30/minute")
async def delete_track_image(
    request: Request,
    game: AssetGameCode,
    track: str,
    _: object = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    config = await get_race_assets(session)
    game_config = config.games.get(game)
    track_name = track.strip()
    if not track_name:
        raise HTTPException(status_code=400, detail="Track is required")
    if game_config is None:
        raise HTTPException(status_code=404, detail="Game assets not found")

    image_key = next((key for key in game_config.track_images if key.lower() == track_name.lower()), track_name)
    previous = game_config.track_images.get(image_key)
    game_config.track_images = {key: value for key, value in game_config.track_images.items() if key.lower() != track_name.lower()}
    if game == "ACC":
        config.track_images = dict(game_config.track_images)
        config.track_ids = dict(game_config.track_ids)
    saved = await save_race_assets(session, config)
    remove_track_image_file(previous)
    return saved
