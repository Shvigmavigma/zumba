import asyncio
import hashlib
import json
import os
import re
import shutil
import time
import zipfile
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.config import get_settings


settings = get_settings()
USER_LIVERY_DIR = Path(settings.upload_dir) / "pilot-liveries"
USER_LIVERY_UPLOAD_SESSION_DIR = Path(settings.upload_dir) / "pilot-livery-upload-sessions"
MAX_LIVERY_IMAGES = 4
MAX_ARCHIVE_FILES = 5000
CHUNK_SIZE = 1024 * 1024
UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024
UPLOAD_BATCH_MAX_BYTES = 48 * 1024 * 1024
UPLOAD_BATCH_MAX_PARTS = 100
UPLOAD_SESSION_TTL_SECONDS = 60 * 60
MAX_UPLOAD_MANIFEST_BYTES = 4 * 1024 * 1024
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


def user_livery_upload_session_dir(user_id: int, session_id: str, root: Path | None = None) -> Path | None:
    if not re.fullmatch(r"[0-9a-f]{32}", session_id):
        return None
    base = root or USER_LIVERY_UPLOAD_SESSION_DIR
    user_dir = base / str(user_id)
    session_dir = user_dir / session_id
    try:
        session_dir.resolve().relative_to(user_dir.resolve())
    except (OSError, ValueError):
        return None
    return session_dir


def _cleanup_expired_upload_sessions(root: Path | None = None) -> None:
    base = root or USER_LIVERY_UPLOAD_SESSION_DIR
    try:
        user_dirs = list(base.iterdir())
    except FileNotFoundError:
        return
    cutoff = time.time() - UPLOAD_SESSION_TTL_SECONDS
    for user_dir in user_dirs:
        if not user_dir.is_dir():
            continue
        for session_dir in user_dir.iterdir():
            if not session_dir.is_dir():
                continue
            try:
                if session_dir.stat().st_mtime < cutoff:
                    shutil.rmtree(session_dir, ignore_errors=True)
            except OSError:
                continue


def _load_upload_session(user_id: int, session_id: str, root: Path | None = None) -> tuple[Path, dict]:
    session_dir = user_livery_upload_session_dir(user_id, session_id, root)
    if session_dir is None or not session_dir.is_dir():
        raise HTTPException(status_code=404, detail="Livery upload session not found")
    try:
        if time.time() - session_dir.stat().st_mtime > UPLOAD_SESSION_TTL_SECONDS:
            shutil.rmtree(session_dir, ignore_errors=True)
            raise HTTPException(status_code=404, detail="Livery upload session expired")
        metadata = json.loads((session_dir / "manifest.json").read_text(encoding="utf-8"))
    except HTTPException:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=404, detail="Livery upload session not found") from exc
    if not isinstance(metadata, dict) or not isinstance(metadata.get("files"), list):
        raise HTTPException(status_code=404, detail="Livery upload session not found")
    return session_dir, metadata


def get_user_livery_upload_session(user_id: int, session_id: str, root: Path | None = None) -> tuple[Path, dict]:
    return _load_upload_session(user_id, session_id, root)


async def create_user_livery_upload_session(
    user_id: int,
    car_file: UploadFile,
    manifest_file: UploadFile,
    images: list[UploadFile],
    *,
    max_archive_mb: int,
    max_image_mb: int,
    requested_session_id: str | None = None,
    root: Path | None = None,
) -> str:
    if not (car_file.filename or "").lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Choose one .json file from the ACC Cars folder")
    car_bytes = await car_file.read(MAX_CAR_JSON_BYTES + 1)
    if not car_bytes:
        raise HTTPException(status_code=400, detail="Car JSON file is empty")
    if len(car_bytes) > MAX_CAR_JSON_BYTES:
        raise HTTPException(status_code=413, detail="Car JSON file is larger than 5 MB")
    skin_folder = skin_folder_from_car_json(car_bytes)
    car_filename = _car_json_filename(car_file.filename)

    manifest_bytes = await manifest_file.read(MAX_UPLOAD_MANIFEST_BYTES + 1)
    if len(manifest_bytes) > MAX_UPLOAD_MANIFEST_BYTES:
        raise HTTPException(status_code=413, detail="Livery file list is too large")
    try:
        raw_manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Livery file list is invalid") from exc
    if not isinstance(raw_manifest, list) or not raw_manifest or len(raw_manifest) > MAX_ARCHIVE_FILES:
        raise HTTPException(status_code=400, detail=f"Choose between 1 and {MAX_ARCHIVE_FILES} livery files")

    files: list[dict] = []
    total_bytes = 0
    for item in raw_manifest:
        if not isinstance(item, dict) or not isinstance(item.get("size"), int) or isinstance(item.get("size"), bool) or item["size"] < 0:
            raise HTTPException(status_code=400, detail="Livery file list contains an invalid file size")
        if not isinstance(item.get("path"), str):
            raise HTTPException(status_code=400, detail="Livery file list contains an invalid path")
        path = _livery_member_name(item["path"], skin_folder)
        files.append({"path": path, "size": item["size"]})
        total_bytes += item["size"]
    if len({item["path"].casefold() for item in files}) != len(files):
        raise HTTPException(status_code=400, detail="Livery folder contains duplicate file names")
    if total_bytes > max_archive_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Livery archive is larger than {max_archive_mb} MB")

    if len(images) > MAX_LIVERY_IMAGES:
        raise HTTPException(status_code=400, detail=f"A livery can have at most {MAX_LIVERY_IMAGES} preview images")
    image_metadata: list[dict] = []
    image_data: list[bytes] = []
    for index, image in enumerate(images):
        extension = _image_extension(image)
        original_name = PurePosixPath((image.filename or "").replace("\\", "/")).name[:255]
        content = await image.read(max_image_mb * 1024 * 1024 + 1)
        if len(content) > max_image_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"A livery image is larger than {max_image_mb} MB")
        if not _image_signature_matches(extension, content[:12]):
            raise HTTPException(status_code=415, detail="Preview file content does not match its image type")
        image_path = f"images/{index}{extension}"
        image_metadata.append({"path": image_path, "original_filename": original_name})
        image_data.append(content)

    session_id = requested_session_id or uuid4().hex
    if not re.fullmatch(r"[0-9a-f]{32}", session_id):
        raise HTTPException(status_code=400, detail="Livery upload session ID is invalid")
    fingerprint = hashlib.sha256()
    fingerprint.update(car_bytes)
    fingerprint.update(json.dumps({"car": car_filename, "files": files, "images": image_metadata}, separators=(",", ":")).encode())
    for content in image_data:
        fingerprint.update(content)

    base = root or USER_LIVERY_UPLOAD_SESSION_DIR
    user_dir = base / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_expired_upload_sessions(base)
    session_dir = user_livery_upload_session_dir(user_id, session_id, base)
    assert session_dir is not None
    if session_dir.is_dir():
        _, existing_metadata = _load_upload_session(user_id, session_id, base)
        if existing_metadata.get("fingerprint") == fingerprint.hexdigest():
            return session_id
        raise HTTPException(status_code=409, detail="Livery upload session ID is already in use")
    # A new upload replaces abandoned staging data; only one livery can be active per pilot.
    for previous_session in user_dir.iterdir():
        if previous_session.is_dir():
            shutil.rmtree(previous_session, ignore_errors=True)
    metadata = {
        "car_filename": car_filename,
        "skin_folder": skin_folder,
        "files": files,
        "images": image_metadata,
        "fingerprint": fingerprint.hexdigest(),
    }
    try:
        session_dir.mkdir()
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail="Livery upload session is already being created") from exc
    try:
        (session_dir / "chunks").mkdir()
        (session_dir / "images").mkdir()
        await asyncio.to_thread((session_dir / "car.json").write_bytes, car_bytes)
        for image_path, content in zip(image_metadata, image_data, strict=True):
            await asyncio.to_thread((session_dir / image_path["path"]).write_bytes, content)
        await asyncio.to_thread(
            (session_dir / "manifest.json").write_text,
            json.dumps(metadata, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        shutil.rmtree(session_dir, ignore_errors=True)
        raise
    return session_id


async def store_user_livery_upload_chunks(
    user_id: int,
    session_id: str,
    file_indexes: list[int],
    offsets: list[int],
    chunks: list[UploadFile],
    *,
    root: Path | None = None,
) -> int:
    session_dir, metadata = _load_upload_session(user_id, session_id, root)
    if (session_dir / ".finalizing").exists():
        raise HTTPException(status_code=409, detail="Livery upload is being finalized")
    if not chunks or len(chunks) > UPLOAD_BATCH_MAX_PARTS or len(chunks) != len(file_indexes) or len(chunks) != len(offsets):
        raise HTTPException(status_code=400, detail="Livery upload batch is invalid")

    entries = metadata["files"]
    batch_size = 0
    seen_chunks: set[tuple[int, int]] = set()
    stored_chunks = 0
    for file_index, offset, upload in zip(file_indexes, offsets, chunks, strict=True):
        if isinstance(file_index, bool) or not isinstance(file_index, int) or not 0 <= file_index < len(entries):
            raise HTTPException(status_code=400, detail="Livery upload batch contains an invalid file index")
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0 or offset % UPLOAD_CHUNK_SIZE:
            raise HTTPException(status_code=400, detail="Livery upload batch contains an invalid chunk offset")
        file_size = entries[file_index]["size"]
        if offset >= file_size:
            raise HTTPException(status_code=400, detail="Livery upload batch contains an out-of-range chunk")
        expected_size = min(UPLOAD_CHUNK_SIZE, file_size - offset)
        if (file_index, offset) in seen_chunks:
            raise HTTPException(status_code=400, detail="Livery upload batch contains a duplicate chunk")
        seen_chunks.add((file_index, offset))
        content = await upload.read(UPLOAD_CHUNK_SIZE + 1)
        if len(content) != expected_size:
            raise HTTPException(status_code=400, detail="Livery upload chunk size does not match the file list")
        batch_size += len(content)
        if batch_size > UPLOAD_BATCH_MAX_BYTES:
            raise HTTPException(status_code=413, detail="Livery upload batch is larger than 48 MB")
        target = session_dir / "chunks" / f"{file_index}-{offset}.part"
        stored_chunks += 1
        await asyncio.to_thread(_store_upload_chunk, target, content)
    os.utime(session_dir, None)
    return stored_chunks


def _store_upload_chunk(target: Path, content: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}-{uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as output:
            output.write(content)
        try:
            os.link(temporary, target)
        except FileExistsError:
            if target.stat().st_size != len(content) or target.read_bytes() != content:
                raise HTTPException(status_code=409, detail="A different livery chunk already exists")
    finally:
        temporary.unlink(missing_ok=True)


def build_user_livery_upload_archive(
    user_id: int,
    session_id: str,
    *,
    max_archive_mb: int,
    root: Path | None = None,
) -> Path:
    session_dir, metadata = _load_upload_session(user_id, session_id, root)
    lock_path = session_dir / ".finalizing"
    try:
        with lock_path.open("x", encoding="utf-8"):
            pass
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail="Livery upload is already being finalized") from exc

    archive_path = session_dir / "liveries.zip"
    max_archive_bytes = max_archive_mb * 1024 * 1024
    total_bytes = 0
    try:
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for file_index, item in enumerate(metadata["files"]):
                filename = item["path"]
                expected_file_size = item["size"]
                with archive.open(filename, "w", force_zip64=True) as entry:
                    offset = 0
                    while offset < expected_file_size:
                        expected_chunk_size = min(UPLOAD_CHUNK_SIZE, expected_file_size - offset)
                        chunk_path = session_dir / "chunks" / f"{file_index}-{offset}.part"
                        if not chunk_path.is_file() or chunk_path.stat().st_size != expected_chunk_size:
                            raise HTTPException(status_code=400, detail="Livery upload is incomplete; retry the missing chunks")
                        total_bytes += expected_chunk_size
                        if total_bytes > max_archive_bytes:
                            raise HTTPException(status_code=413, detail=f"Livery archive is larger than {max_archive_mb} MB")
                        with chunk_path.open("rb") as source:
                            shutil.copyfileobj(source, entry, length=CHUNK_SIZE)
                        offset += expected_chunk_size
        os.utime(session_dir, None)
        return archive_path
    except Exception:
        archive_path.unlink(missing_ok=True)
        raise
    finally:
        lock_path.unlink(missing_ok=True)


def remove_user_livery_upload_session(user_id: int, session_id: str, root: Path | None = None) -> None:
    session_dir = user_livery_upload_session_dir(user_id, session_id, root)
    if session_dir is None:
        return
    try:
        session_dir.resolve().relative_to((root or USER_LIVERY_UPLOAD_SESSION_DIR).resolve())
    except (OSError, ValueError):
        return
    shutil.rmtree(session_dir, ignore_errors=True)


def _write_livery_archive(
    archive_path: Path,
    uploads: list[UploadFile],
    member_names: list[str],
    max_archive_mb: int,
) -> int:
    """Write the uploaded files without blocking the async request event loop."""
    total_bytes = 0
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for upload, member_name in zip(uploads, member_names, strict=True):
            upload.file.seek(0)
            with archive.open(member_name, "w", force_zip64=True) as entry:
                while chunk := upload.file.read(CHUNK_SIZE):
                    total_bytes += len(chunk)
                    if total_bytes > max_archive_mb * 1024 * 1024:
                        raise HTTPException(status_code=413, detail=f"Livery archive is larger than {max_archive_mb} MB")
                    entry.write(chunk)
    return total_bytes


async def create_user_livery_package(
    user_id: int,
    car_file: UploadFile,
    livery_files: list[UploadFile],
    images: list[UploadFile],
    *,
    max_archive_mb: int,
    max_image_mb: int,
    root: Path | None = None,
    prebuilt_livery_archive: Path | None = None,
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

    if not livery_files and prebuilt_livery_archive is None:
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
    try:
        staging_dir.mkdir()
        cars_archive = staging_dir / "cars.zip"
        with zipfile.ZipFile(cars_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
            archive.writestr(car_filename, car_bytes)

        liveries_archive = staging_dir / "liveries.zip"
        if prebuilt_livery_archive is not None:
            if not prebuilt_livery_archive.is_file():
                raise HTTPException(status_code=400, detail="Livery upload archive is not available")
            await asyncio.to_thread(shutil.copyfile, prebuilt_livery_archive, liveries_archive)
        else:
            await asyncio.to_thread(_write_livery_archive, liveries_archive, livery_files, member_names, max_archive_mb)

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
