import asyncio
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.config import get_settings

MAX_DATABASE_DUMP_BYTES = 300 * 1024 * 1024


def _remove_backup(path: str) -> None:
    Path(path).unlink(missing_ok=True)


def _postgres_environment() -> dict[str, str]:
    settings = get_settings()
    parsed = urlparse(settings.database_url.replace("+asyncpg", "", 1))
    database = unquote(parsed.path.lstrip("/").split("?", 1)[0])
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname or not database:
        raise HTTPException(status_code=503, detail="Database backup is not configured")

    environment = os.environ.copy()
    environment.update(
        {
            "PGHOST": parsed.hostname,
            "PGPORT": str(parsed.port or 5432),
            "PGUSER": unquote(parsed.username or ""),
            "PGPASSWORD": unquote(parsed.password or ""),
            "PGDATABASE": database,
        }
    )
    return environment


async def create_database_backup() -> FileResponse:
    file_descriptor, path = tempfile.mkstemp(prefix="bmrl-database-", suffix=".dump")
    os.close(file_descriptor)
    try:
        with open(path, "wb") as output:
            process = await asyncio.create_subprocess_exec(
                "pg_dump",
                "--format=custom",
                "--no-owner",
                "--no-privileges",
                env=_postgres_environment(),
                stdout=output,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()
        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip() or "pg_dump failed"
            raise HTTPException(status_code=502, detail=f"Database backup failed: {detail}")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="pg_dump is not installed in the backend image") from exc
    except HTTPException:
        _remove_backup(path)
        raise
    except Exception:
        _remove_backup(path)
        raise

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=f"bmrl-database-{timestamp}.dump",
        background=BackgroundTask(_remove_backup, path),
    )


async def restore_database_backup(file: UploadFile) -> None:
    environment = _postgres_environment()
    file_descriptor, path = tempfile.mkstemp(prefix="bmrl-restore-", suffix=".dump")
    try:
        size = 0
        with os.fdopen(file_descriptor, "wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_DATABASE_DUMP_BYTES:
                    raise HTTPException(status_code=413, detail="Database dump is larger than 300 MB")
                output.write(chunk)

        if size < 5:
            raise HTTPException(status_code=400, detail="Database dump is empty or invalid")
        with open(path, "rb") as dump:
            if dump.read(5) != b"PGDMP":
                raise HTTPException(status_code=415, detail="Upload a custom-format PostgreSQL .dump file")

        async def run_pg_restore(*args: str) -> tuple[int, bytes]:
            try:
                process = await asyncio.create_subprocess_exec(
                    "pg_restore",
                    *args,
                    env=environment,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                )
            except FileNotFoundError as exc:
                raise HTTPException(status_code=503, detail="pg_restore is not installed in the backend image") from exc
            try:
                _, stderr = await asyncio.wait_for(process.communicate(), timeout=900)
            except asyncio.TimeoutError as exc:
                process.kill()
                await process.communicate()
                raise HTTPException(status_code=504, detail="Database restore timed out; changes were rolled back") from exc
            return process.returncode or 0, stderr

        check_code, _ = await run_pg_restore("--list", path)
        if check_code:
            raise HTTPException(status_code=400, detail="The uploaded PostgreSQL dump is invalid")

        restore_code, _ = await run_pg_restore(
            "--dbname",
            environment["PGDATABASE"],
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "--single-transaction",
            "--exit-on-error",
            path,
        )
        if restore_code:
            raise HTTPException(status_code=400, detail="Restore failed; the existing database was rolled back")
    finally:
        await file.close()
        _remove_backup(path)
