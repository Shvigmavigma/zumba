from datetime import datetime
import re
from random import randint
from time import monotonic

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.deps import require_admin
from app.models import AppSetting, User
from app.rate_limit import limiter
from app.schemas import TwitchConfigRead, TwitchConfigUpdate, TwitchStatus


router = APIRouter()
settings = get_settings()
_status_cache: tuple[float, TwitchStatus] | None = None
_token_cache: tuple[float, str] | None = None
TWITCH_FALLBACK_VIDEO_KEY = "twitch_fallback_video"
TWITCH_WEB_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"


def clear_status_cache() -> None:
    global _status_cache
    _status_cache = None


def parse_twitch_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def thumbnail_url(value: str | None) -> str | None:
    if not value:
        return None
    normalized = (
        value.replace("%{width}", "640")
        .replace("%{height}", "360")
        .replace("{width}", "640")
        .replace("{height}", "360")
    )
    return re.sub(
        r"thumb\d+(-640x360\.jpg)$",
        lambda match: f"thumb{randint(0, 3)}{match.group(1)}",
        normalized,
    )


def normalize_twitch_video_id(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    if ("://" in cleaned or "www." in cleaned) and "twitch.tv" not in cleaned.lower():
        raise HTTPException(status_code=422, detail="Use a Twitch video URL or numeric video ID")
    match = re.search(r"(?:videos/|video=|[?&]v=|^v?)(\d{4,})", cleaned, re.IGNORECASE)
    if not match:
        raise HTTPException(status_code=422, detail="Use a Twitch video URL or numeric video ID")
    return match.group(1)


def video_url(video_id: str) -> str:
    return f"https://www.twitch.tv/videos/{video_id}"


def config_from_value(value: dict | None) -> TwitchConfigRead:
    if not isinstance(value, dict):
        return TwitchConfigRead()
    video_id = str(value.get("fallback_video_id") or "").strip()
    title = str(value.get("fallback_video_title") or "").strip()
    stored_thumbnail = str(value.get("fallback_video_thumbnail_url") or "").strip()
    return TwitchConfigRead(
        fallback_video_url=video_url(video_id) if video_id else "",
        fallback_video_id=video_id,
        fallback_video_title=title,
        fallback_video_thumbnail_url=stored_thumbnail,
    )


async def get_twitch_config_value(session: AsyncSession) -> TwitchConfigRead:
    setting = await session.get(AppSetting, TWITCH_FALLBACK_VIDEO_KEY)
    return config_from_value(setting.value if setting is not None else None)


def fallback_video_status(base_status: TwitchStatus, config: TwitchConfigRead) -> TwitchStatus | None:
    if not config.fallback_video_id:
        return None
    return TwitchStatus(
        channel_login=base_status.channel_login,
        channel_url=base_status.channel_url,
        is_configured=base_status.is_configured,
        is_live=False,
        status="vod",
        embed_type="video",
        embed_value=f"v{config.fallback_video_id}",
        external_url=config.fallback_video_url,
        title=config.fallback_video_title or None,
        thumbnail_url=config.fallback_video_thumbnail_url or None,
    )


def video_metadata_from_payload(video: dict | None) -> dict[str, str]:
    if not video:
        return {}
    return {
        "title": video.get("title") or "",
        "thumbnail_url": thumbnail_url(video.get("thumbnail_url")) or "",
    }


def fallback_status() -> TwitchStatus:
    channel_login = settings.twitch_channel_login.strip() or "bmrlracing"
    channel_url = f"https://www.twitch.tv/{channel_login}"
    return TwitchStatus(
        channel_login=channel_login,
        channel_url=channel_url,
        is_configured=bool(settings.twitch_client_id and settings.twitch_client_secret),
        is_live=False,
        status="channel",
        embed_type="channel",
        embed_value=channel_login,
        external_url=channel_url,
    )


@router.get("/config", response_model=TwitchConfigRead)
@limiter.limit("120/minute")
async def get_twitch_config(
    request: Request,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await get_twitch_config_value(session)


@router.patch("/config", response_model=TwitchConfigRead)
@limiter.limit("20/minute")
async def update_twitch_config(
    payload: TwitchConfigUpdate,
    request: Request,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    video_id = normalize_twitch_video_id(payload.fallback_video_url) if payload.fallback_video_url.strip() else ""
    metadata = await load_twitch_video_metadata(video_id) if video_id else {}
    value = {
        "fallback_video_id": video_id,
        "fallback_video_title": payload.fallback_video_title.strip() or metadata.get("title", ""),
        "fallback_video_thumbnail_url": metadata.get("thumbnail_url", ""),
    }
    setting = await session.get(AppSetting, TWITCH_FALLBACK_VIDEO_KEY)
    if setting is None:
        setting = AppSetting(key=TWITCH_FALLBACK_VIDEO_KEY, value=value)
        session.add(setting)
    else:
        setting.value = value
    await session.commit()
    clear_status_cache()
    return config_from_value(value)


async def get_app_access_token(client: httpx.AsyncClient) -> str | None:
    global _token_cache
    if not settings.twitch_client_id or not settings.twitch_client_secret:
        return None

    now = monotonic()
    if _token_cache is not None and now < _token_cache[0]:
        return _token_cache[1]

    response = await client.post(
        "https://id.twitch.tv/oauth2/token",
        data={
            "client_id": settings.twitch_client_id,
            "client_secret": settings.twitch_client_secret,
            "grant_type": "client_credentials",
        },
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        return None

    expires_in = int(payload.get("expires_in") or 3600)
    _token_cache = (now + max(60, expires_in - 60), token)
    return token


async def helix_get(client: httpx.AsyncClient, token: str, path: str, params: dict[str, str]) -> dict:
    response = await client.get(
        f"https://api.twitch.tv/helix/{path}",
        params=params,
        headers={
            "Authorization": f"Bearer {token}",
            "Client-Id": settings.twitch_client_id,
        },
    )
    response.raise_for_status()
    return response.json()


async def load_twitch_video_metadata(video_id: str) -> dict[str, str]:
    if not settings.twitch_client_id or not settings.twitch_client_secret:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                return await load_twitch_video_metadata_from_web(client, video_id, strict=True)
        except httpx.HTTPError:
            return {}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            token = await get_app_access_token(client)
            if not token:
                return {}
            videos = await helix_get(client, token, "videos", {"id": video_id})
    except httpx.HTTPError:
        return {}
    video = next(iter(videos.get("data") or []), None)
    if not video:
        raise HTTPException(status_code=422, detail="Twitch video was not found")
    return video_metadata_from_payload(video)


async def load_twitch_video_metadata_from_web(
    client: httpx.AsyncClient, video_id: str, *, strict: bool = False
) -> dict[str, str]:
    response = await client.post(
        "https://gql.twitch.tv/gql",
        json={
            "operationName": "VideoPreview",
            "query": (
                "query VideoPreview($id: ID!) { "
                "video(id: $id) { id title previewThumbnailURL(width: 640, height: 360) } "
                "}"
            ),
            "variables": {"id": video_id},
        },
        headers={"Client-Id": TWITCH_WEB_CLIENT_ID},
    )
    response.raise_for_status()
    video = (response.json().get("data") or {}).get("video")
    if not video:
        if strict:
            raise HTTPException(status_code=422, detail="Twitch video was not found")
        return {}
    return {
        "title": video.get("title") or "",
        "thumbnail_url": thumbnail_url(video.get("previewThumbnailURL")) or "",
    }


@router.get("/status", response_model=TwitchStatus)
@limiter.limit("600/minute")
async def twitch_status(request: Request, session: AsyncSession = Depends(get_session)):
    global _status_cache
    now = monotonic()
    if _status_cache is not None and now < _status_cache[0]:
        return _status_cache[1]

    status = fallback_status()
    twitch_config = await get_twitch_config_value(session)
    configured_video = fallback_video_status(status, twitch_config)
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            token = await get_app_access_token(client)
            if not token:
                if configured_video is not None:
                    if not configured_video.thumbnail_url and twitch_config.fallback_video_id:
                        try:
                            metadata = await load_twitch_video_metadata_from_web(client, twitch_config.fallback_video_id)
                        except httpx.HTTPError:
                            metadata = {}
                        configured_video.thumbnail_url = metadata.get("thumbnail_url") or None
                        if not configured_video.title:
                            configured_video.title = metadata.get("title") or None
                    status = configured_video
                _status_cache = (now + settings.twitch_status_cache_seconds, status)
                return status

            streams = await helix_get(client, token, "streams", {"user_login": status.channel_login})
            live_stream = next(iter(streams.get("data") or []), None)
            if live_stream:
                status = TwitchStatus(
                    channel_login=status.channel_login,
                    channel_url=status.channel_url,
                    is_configured=True,
                    is_live=True,
                    status="live",
                    embed_type="channel",
                    embed_value=status.channel_login,
                    external_url=status.channel_url,
                    title=live_stream.get("title"),
                    game_name=live_stream.get("game_name"),
                    thumbnail_url=thumbnail_url(live_stream.get("thumbnail_url")),
                    viewer_count=live_stream.get("viewer_count"),
                    started_at=parse_twitch_datetime(live_stream.get("started_at")),
                )
                _status_cache = (now + settings.twitch_status_cache_seconds, status)
                return status

            if configured_video is not None:
                if not configured_video.thumbnail_url and twitch_config.fallback_video_id:
                    videos = await helix_get(client, token, "videos", {"id": twitch_config.fallback_video_id})
                    metadata = video_metadata_from_payload(next(iter(videos.get("data") or []), None))
                    configured_video.thumbnail_url = metadata.get("thumbnail_url") or None
                    if not configured_video.title:
                        configured_video.title = metadata.get("title") or None
                _status_cache = (now + min(settings.twitch_status_cache_seconds, 15), configured_video)
                return configured_video

            users = await helix_get(client, token, "users", {"login": status.channel_login})
            user = next(iter(users.get("data") or []), None)
            if user:
                videos = await helix_get(
                    client,
                    token,
                    "videos",
                    {"user_id": user["id"], "type": "archive", "sort": "time", "first": "1"},
                )
                video = next(iter(videos.get("data") or []), None)
                if video:
                    status = TwitchStatus(
                        channel_login=status.channel_login,
                        channel_url=status.channel_url,
                        is_configured=True,
                        is_live=False,
                        status="vod",
                        embed_type="video",
                        embed_value=f"v{video['id']}",
                        external_url=video.get("url") or status.channel_url,
                        title=video.get("title"),
                        thumbnail_url=thumbnail_url(video.get("thumbnail_url")),
                        viewer_count=video.get("view_count"),
                        published_at=parse_twitch_datetime(video.get("published_at") or video.get("created_at")),
                    )
    except httpx.HTTPError:
        status = fallback_status()

    _status_cache = (now + settings.twitch_status_cache_seconds, status)
    return status
