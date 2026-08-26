import asyncio
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

from fastapi import HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.config import get_settings


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
