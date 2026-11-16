import asyncio
import base64
import configparser
import math
import re
import logging
from time import time
from urllib.parse import urlsplit

import httpx
import orjson
import websockets
from fastapi import APIRouter, HTTPException, Response, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import get_settings

router = APIRouter()
settings = get_settings()
_origin = settings.ac_timing_origin.rstrip("/")
_cache_key = f"bmrl:ac-timing:v2:{_origin}"
_store = Redis.from_url(settings.rate_limit_storage_uri, socket_timeout=1) if (settings.rate_limit_storage_uri or "").startswith(("redis://", "rediss://")) else None
_lock = asyncio.Lock()
_local = {}
_map_cache = {}
logger = logging.getLogger(__name__)

@router.websocket("/positions")
async def positions(websocket: WebSocket):
    await websocket.accept()
    origin = urlsplit(_origin)
    scheme = "wss" if origin.scheme == "https" else "ws"
    try:
        async with websockets.connect(f"{scheme}://{origin.netloc}/api/race-control", open_timeout=8) as upstream:
            async for raw in upstream:
                event = orjson.loads(raw)
                data = event.get("Message") or {}
                if event.get("EventType") == 200:
                    session = data.get("SessionInfo") or {}
                    await websocket.send_json({"track": session.get("Track"), "layout": session.get("TrackConfig") or ""})
                elif event.get("EventType") == 50:
                    break
                elif event.get("EventType") == 53:
                    pos = data.get("Pos") or {}
                    x, z = pos.get("X"), pos.get("Z")
                    if isinstance(x, (int, float)) and isinstance(z, (int, float)) and math.isfinite(x) and math.isfinite(z):
                        await websocket.send_json({"slot": data.get("CarID"), "x": x, "z": z})
    except (WebSocketDisconnect, websockets.exceptions.WebSocketException, OSError, ValueError, TypeError, KeyError):
        pass
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass


def splits(values):
    values = values or {}
    return [(values.get(str(i)) or {}).get("SplitTime", 0) / 1_000_000 for i in range(3)]


def public_driver(driver, online):
    info = driver["CarInfo"]
    car = (driver.get("Cars") or {}).get(info.get("CarModel")) or {}
    pos = driver.get("LastPos") or {}
    return {
        "name": info.get("DriverName"), "car": info.get("CarName") or info.get("CarModel"),
        "slot": info.get("CarID"), "position": driver.get("Position"), "online": online,
        "laps": driver.get("TotalNumLaps"), "pit": driver.get("IsInPits"),
        "x": pos.get("X"), "z": pos.get("Z"),
        "last": (car.get("LastLap") or 0) / 1_000_000, "best": (car.get("BestLap") or 0) / 1_000_000,
        "current": splits(car.get("CurrentLapSplits")), "bestSectors": splits(car.get("BestLapSplits")),
        "personalSectors": splits(car.get("BestSplits")),
        "currentSectorFlags": [
            {"session": bool(item.get("IsBest")), "personal": bool(item.get("IsDriversBest")), "cuts": bool(item.get("Cuts"))}
            for item in ((car.get("CurrentLapSplits") or {}).get(str(i)) or {} for i in range(3))
        ],
    }


async def refresh(previous):
    now = time()
    if now < previous.get("retryAt", 0):
        return previous
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(f"{_origin}/api/live-timings/leaderboard.json")
            response.raise_for_status()
            raw = response.json()
        if not raw["Track"]:
            raise ValueError("No active track")
        drivers = [public_driver(d, online) for key, online in (("ConnectedDrivers", True), ("DisconnectedDrivers", False))
                   for d in (raw.get(key) or []) if not d["CarInfo"].get("IsSpectator")]
        session = {"track": raw["Track"], "layout": raw.get("TrackConfig") or "", "name": raw.get("Name"),
                   "air": raw.get("AmbientTemp"), "road": raw.get("RoadTemp"), "drivers": drivers}
        return {"active": True, "stale": False, "session": session, "updated": time(), "retryAt": time() + 16}
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
        logger.warning("Live timing update failed: %s", exc)
        session = previous.get("session") if now - previous.get("updated", 0) < 60 else None
        retry_at = now + 5
        if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
            try:
                retry_at = max(retry_at, float(exc.response.headers.get("x-ratelimit-reset", 0)) + 1)
            except ValueError:
                pass
        if session:
            retry_at = min(retry_at, previous["updated"] + 60)
        return {"active": bool(session), "stale": bool(session), "session": session,
                "updated": previous.get("updated", 0), "retryAt": retry_at}


async def snapshot():
    global _local
    async with _lock:
        if time() < _local.get("retryAt", 0):
            return _local
        if _store is not None:
            try:
                cached = orjson.loads(await _store.get(_cache_key) or b"{}")
                if time() < cached.get("retryAt", 0):
                    _local = cached
                    return cached
                async with _store.lock(_cache_key + ":lock", timeout=15, blocking_timeout=5):
                    cached = orjson.loads(await _store.get(_cache_key) or b"{}")
                    _local = await refresh(cached or _local)
                    await _store.set(_cache_key, orjson.dumps(_local), ex=65)
                    return _local
            except RedisError:
                pass
        _local = await refresh(_local)
        return _local


@router.get("")
async def timing(response: Response, status_only: bool = False):
    data = await snapshot()
    response.headers["Cache-Control"] = "no-store"
    result = {"active": data["active"], "stale": data.get("stale", False), "updated": data["updated"]}
    if not status_only:
        result["session"] = data["session"]
    return result


@router.get("/map")
async def track_map(response: Response, track: str, layout: str = ""):
    session = (await snapshot()).get("session") or {}
    if (track, layout) != (session.get("track"), session.get("layout")) or not all(
        re.fullmatch(r"[a-zA-Z0-9_-]+", part) for part in (track, layout) if part
    ):
        raise HTTPException(404, "Track unavailable")
    key = (track, layout)
    response.headers["Cache-Control"] = "public, max-age=600"
    if key in _map_cache:
        return _map_cache[key]
    url = f"{_origin}/content/tracks/{track}" + (f"/{layout}" if layout else "")
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            image, ini = await asyncio.gather(client.get(url + "/map.png"), client.get(url + "/data/map.ini"))
        image.raise_for_status()
        ini.raise_for_status()
        if not image.content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Invalid map image")
        parser = configparser.ConfigParser()
        parser.read_string(ini.text.lstrip("\ufeff"))
        params = parser["PARAMETERS"]
        geometry = {k: float(params[k]) for k in ("WIDTH", "HEIGHT", "SCALE_FACTOR", "X_OFFSET", "Z_OFFSET")}
        geometry["PADDING"] = params.getfloat("PADDING", 0)
        if not all(map(math.isfinite, geometry.values())) or min(geometry[k] for k in ("WIDTH", "HEIGHT", "SCALE_FACTOR")) <= 0:
            raise ValueError("Invalid map geometry")
        data = {"geometry": geometry, "image": "data:image/png;base64," + base64.b64encode(image.content).decode()}
    except (httpx.HTTPError, ValueError, KeyError, configparser.Error):
        raise HTTPException(404, "Track map unavailable")
    _map_cache.clear()
    _map_cache[key] = data
    return data
