import json
import re
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.config import get_settings


settings = get_settings()
USER_LIVERY_DIR = Path(settings.upload_dir) / "pilot-liveries"
MAX_LIVERY_IMAGES = 4
MAX_ARCHIVE_FILES = 5000
CHUNK_SIZE = 1024 * 1024
MAX_CAR_JSON_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
WINDOWS_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def _safe_path_component(value: str) -> bool:
    return bool(value) and value not in {".", ".."} and not value.endswith((" ", ".")) and not any(
        ord(char) < 32 or char in '<>:\\"/|?*' for char in value
    ) and value.split(".", 1)[0].upper() not in WINDOWS_RESERVED_NAMES


def skin_folder_from_car_json(data: bytes) -> str:
    try:
        config = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Car file must be a valid ACC JSON file") from exc
    folder = config.get("customSkinName") if isinstance(config, dict) else None
    if not isinstance(folder, str) or not _safe_path_component(folder) or folder != folder.strip():
        raise HTTPException(status_code=400, detail="Car JSON must contain a valid customSkinName folder name")
    return folder


def _car_json_filename(filename: str | None) -> str:
    normalized = (filename or "").replace("\\", "/")
    name = PurePosixPath(normalized).name
    if not name.lower().endswith(".json") or not _safe_path_component(name):
        raise HTTPException(status_code=400, detail="Choose one .json file from the ACC Cars folder")
    return name


def _livery_member_name(filename: str | None, skin_folder: str) -> str:
    normalized = (filename or "").replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        raise HTTPException(status_code=400, detail="Select the complete livery folder, not individual files")
    parts = PurePosixPath(normalized).parts
    if len(parts) < 2 or parts[0] != skin_folder or any(not _safe_path_component(part) for part in parts):
        raise HTTPException(
            status_code=400,
            detail=f"Livery folder must be named exactly '{skin_folder}', as specified by customSkinName in the car JSON",
        )
    return "/".join(parts)


def _image_extension(file: UploadFile) -> str:
    extension = PurePosixPath((file.filename or "").replace("\\", "/")).suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Only PNG, JPG, WEBP and GIF livery images are allowed")
    return ".jpg" if extension == ".jpeg" else extension


def _image_signature_matches(extension: str, header: bytes) -> bool:
    return (
        (extension == ".png" and header.startswith(b"\x89PNG\r\n\x1a\n"))
        or (extension == ".jpg" and header.startswith(b"\xff\xd8\xff"))
        or (extension == ".gif" and header.startswith((b"GIF87a", b"GIF89a")))
        or (extension == ".webp" and len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP")
    )


def user_livery_package_dir(user_id: int, package_id: str, root: Path | None = None) -> Path:
    return (root or USER_LIVERY_DIR) / str(user_id) / package_id


def remove_user_livery_package(user_id: int, package_id: str | None, root: Path | None = None) -> None:
    if not package_id or not re.fullmatch(r"[0-9a-f]{32}", package_id):
        return
    package_dir = user_livery_package_dir(user_id, package_id, root)
    try:
        package_dir.resolve().relative_to((root or USER_LIVERY_DIR).resolve())
    except (OSError, ValueError):
        return
    shutil.rmtree(package_dir, ignore_errors=True)


def prune_user_livery_packages(user_id: int, keep_package_ids: set[str], root: Path | None = None) -> None:
    user_dir = (root or USER_LIVERY_DIR) / str(user_id)
    try:
        packages = list(user_dir.iterdir())
    except FileNotFoundError:
        return
    for package_dir in packages:
        if not package_dir.is_dir() or not re.fullmatch(r"[0-9a-f]{32}", package_dir.name):
            continue
        if package_dir.name not in keep_package_ids:
            shutil.rmtree(package_dir, ignore_errors=True)


def copy_user_livery_images(
    user_id: int,
    previous_package_id: str,
    package_id: str,
    images,
    root: Path | None = None,
) -> list[tuple[str, str]]:
    previous_dir = user_livery_package_dir(user_id, previous_package_id, root) / "images"
    new_dir = user_livery_package_dir(user_id, package_id, root) / "images"
    copied: list[tuple[str, str]] = []
    for image in images:
        filename = PurePosixPath(image.image_url).name
        if not re.fullmatch(r"[0-9a-f]{32}\.(png|jpg|webp|gif)", filename):
            continue
        source = previous_dir / filename
        if not source.is_file():
            continue
        new_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, new_dir / filename)
        copied.append((filename, image.original_filename))
    return copied


def user_livery_asset_path(
    user_id: int,
    package_id: str,
    asset_path: str,
    root: Path | None = None,
) -> Path | None:
    if not re.fullmatch(r"[0-9a-f]{32}", package_id):
        return None
    normalized = asset_path.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if parts not in (("cars.zip",), ("liveries.zip",)) and not (
        len(parts) == 2 and parts[0] == "images" and PurePosixPath(parts[1]).suffix.lower() in ALLOWED_IMAGE_EXTENSIONS
    ):
        return None
    base = user_livery_package_dir(user_id, package_id, root)
    try:
        target = (base / Path(*parts)).resolve()
        target.relative_to(base.resolve())
    except (OSError, ValueError):
        return None
    return target if target.is_file() else None


async def create_user_livery_package(
    user_id: int,
    car_file: UploadFile,
    livery_files: list[UploadFile],
    images: list[UploadFile],
    *,
    max_archive_mb: int,
    max_image_mb: int,
    root: Path | None = None,
) -> tuple[str, str, int, int, list[tuple[str, str]], Path]:
    if not (car_file.filename or "").lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Choose one .json file from the ACC Cars folder")
    car_bytes = await car_file.read(MAX_CAR_JSON_BYTES + 1)
    if not car_bytes:
        raise HTTPException(status_code=400, detail="Car JSON file is empty")
    if len(car_bytes) > MAX_CAR_JSON_BYTES:
        raise HTTPException(status_code=413, detail="Car JSON file is larger than 5 MB")
    skin_folder = skin_folder_from_car_json(car_bytes)
    car_filename = _car_json_filename(car_file.filename)

    if not livery_files:
        raise HTTPException(status_code=400, detail="Choose the complete livery folder")
    if len(livery_files) > MAX_ARCHIVE_FILES:
        raise HTTPException(status_code=413, detail=f"A livery folder can contain at most {MAX_ARCHIVE_FILES} files")
    if len(images) > MAX_LIVERY_IMAGES:
        raise HTTPException(status_code=400, detail=f"A livery can have at most {MAX_LIVERY_IMAGES} preview images")

    member_names = [_livery_member_name(file.filename, skin_folder) for file in livery_files]
    if len({name.casefold() for name in member_names}) != len(member_names):
        raise HTTPException(status_code=400, detail="Livery folder contains duplicate file names")

    package_id = uuid4().hex
    base = root or USER_LIVERY_DIR
    user_dir = base / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = user_dir / f".upload-{uuid4().hex}"
    package_dir = user_livery_package_dir(user_id, package_id, base)
    staged_images: list[tuple[str, str]] = []
    max_archive_bytes = max_archive_mb * 1024 * 1024

    try:
        staging_dir.mkdir()
        cars_archive = staging_dir / "cars.zip"
        with zipfile.ZipFile(cars_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
            archive.writestr(car_filename, car_bytes)

        total_livery_bytes = 0
        liveries_archive = staging_dir / "liveries.zip"
        with zipfile.ZipFile(liveries_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
            for upload, member_name in zip(livery_files, member_names, strict=True):
                await upload.seek(0)
                with archive.open(member_name, "w", force_zip64=True) as entry:
                    while chunk := await upload.read(CHUNK_SIZE):
                        total_livery_bytes += len(chunk)
                        if total_livery_bytes > max_archive_bytes:
                            raise HTTPException(status_code=413, detail=f"Livery archive is larger than {max_archive_mb} MB")
                        entry.write(chunk)

        image_dir = staging_dir / "images"
        if images:
            image_dir.mkdir()
        for image in images:
            extension = _image_extension(image)
            original_name = PurePosixPath((image.filename or "").replace("\\", "/")).name[:255]
            header = await image.read(12)
            if not _image_signature_matches(extension, header):
                raise HTTPException(status_code=415, detail="Preview file content does not match its image type")
            await image.seek(0)
            asset_name = f"{uuid4().hex}{extension}"
            total_image_bytes = 0
            with (image_dir / asset_name).open("wb") as output:
                while chunk := await image.read(CHUNK_SIZE):
                    total_image_bytes += len(chunk)
                    if total_image_bytes > max_image_mb * 1024 * 1024:
                        raise HTTPException(status_code=413, detail=f"A livery image is larger than {max_image_mb} MB")
                    output.write(chunk)
            staged_images.append((asset_name, original_name))

        cars_size = cars_archive.stat().st_size
        liveries_size = liveries_archive.stat().st_size
        staging_dir.replace(package_dir)
        return package_id, skin_folder, cars_size, liveries_size, staged_images, package_dir
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise
