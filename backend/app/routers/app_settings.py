import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.deps import require_admin, require_news_editor
from app.models import AppSetting, User
from app.rate_limit import limiter, set_request_limits
from app.schemas import BrandingSettingsRead, BrandingSettingsUpdate, DonationSettingsRead, DonationSettingsUpdate, LicenseSettingsRead, LicenseSettingsUpdate, NewsSettingsRead, NewsSettingsUpdate, SystemSettingsRead, SystemSettingsUpdate, WeatherSettingsRead
from app.services import DEFAULT_RATING_CHANGE_COEFFICIENT, recalculate_all_ratings


router = APIRouter()
settings = get_settings()

DONATION_SETTINGS_KEY = "donation_settings"
LICENSE_SETTINGS_KEY = "license_settings"
BRANDING_SETTINGS_KEY = "branding_settings"
SYSTEM_SETTINGS_KEY = "system_settings"
NEWS_SETTINGS_KEY = "news_settings"
WEATHER_SETTINGS_KEY = "weather_settings"
LOGO_UPLOAD_DIR = Path(settings.upload_dir) / "logos"
BRANDING_DIR = Path(settings.branding_dir)
BRANDING_METADATA_FILE = BRANDING_DIR / "site.env"
BROWSER_LOGO_UPLOAD_DIR = BRANDING_DIR / "browser-logos"
WEATHER_UPLOAD_DIR = Path(settings.upload_dir) / "weather"
DEFAULT_LOGOS = {
    "light_logo_url": "/assets/bmrl-logo-light-cutout.png",
    "dark_logo_url": "/assets/bmrl-logo-dark-cutout.png",
}
DEFAULT_AVATAR_URL = "/assets/avatar-template.jpg"
DEFAULT_BROWSER_TITLE = "BMRL - BeamMP Racing League"
DEFAULT_BROWSER_DESCRIPTION = "BMRL is a BeamMP racing league featuring championships, race results, drivers and teams."
DEFAULT_BROWSER_ICON_URL = "/api/app-settings/branding/browser-icon"
DEFAULT_REQUESTS_PER_USER_PER_MINUTE = 1200
DEFAULT_REQUESTS_PER_IP_PER_MINUTE = 1200
DEFAULT_SR_PER_RACE = 0.3
# Kept as an import-compatible alias for older callers.
DEFAULT_SR_CHANGE_COEFFICIENT = DEFAULT_RATING_CHANGE_COEFFICIENT
DEFAULT_NEWS_AUTO_ROTATE_SECONDS = 30
DEFAULT_NEWS_MANUAL_PAUSE_SECONDS = 300
ALLOWED_LOGO_MEDIA_TYPES = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def site_metadata_from_file() -> dict[str, str]:
    metadata = {
        "browser_title": DEFAULT_BROWSER_TITLE,
        "browser_description": DEFAULT_BROWSER_DESCRIPTION,
    }
    try:
        lines = BRANDING_METADATA_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return metadata

    for line in lines:
        key, separator, raw_value = line.partition("=")
        if not separator or key.strip() not in {"SITE_TITLE", "SITE_DESCRIPTION"}:
            continue
        raw_value = raw_value.strip()
        if raw_value.startswith('"'):
            try:
                parsed = json.loads(raw_value)
                if isinstance(parsed, str):
                    raw_value = parsed
            except json.JSONDecodeError:
                pass
        elif len(raw_value) >= 2 and raw_value[0] == raw_value[-1] == "'":
            raw_value = raw_value[1:-1]
        field = "browser_title" if key.strip() == "SITE_TITLE" else "browser_description"
        limit = 120 if field == "browser_title" else 320
        metadata[field] = raw_value.strip()[:limit]

    metadata["browser_title"] = metadata["browser_title"] or DEFAULT_BROWSER_TITLE
    return metadata


def write_site_metadata(browser_title: str, browser_description: str) -> None:
    BRANDING_DIR.mkdir(parents=True, exist_ok=True)
    temporary = BRANDING_METADATA_FILE.with_name(f".site-{uuid4().hex}.tmp")
    temporary.write_text(
        f"SITE_TITLE={json.dumps(browser_title, ensure_ascii=False)}\n"
        f"SITE_DESCRIPTION={json.dumps(browser_description, ensure_ascii=False)}\n",
        encoding="utf-8",
    )
    temporary.replace(BRANDING_METADATA_FILE)


def browser_icon_file_url(path: Path) -> str:
    return f"{DEFAULT_BROWSER_ICON_URL}?v={path.name}"


def latest_browser_icon_path() -> Path | None:
    candidates = (
        path for path in BROWSER_LOGO_UPLOAD_DIR.glob("browser-icon-*")
        if path.is_file() and path.suffix.lower() in ALLOWED_LOGO_MEDIA_TYPES.values()
    )
    return max(candidates, key=lambda path: path.name, default=None)


def migrate_legacy_browser_icon(value: dict) -> None:
    legacy_url = str(value.get("browser_icon_url") or "")
    legacy_path = urlsplit(legacy_url).path
    prefix = "/api/uploads/logos/"
    if not legacy_path.startswith(prefix):
        return
    filename = Path(legacy_path).name
    if not filename.startswith("browser-icon-") or Path(filename).suffix.lower() not in ALLOWED_LOGO_MEDIA_TYPES.values():
        return
    source = LOGO_UPLOAD_DIR / filename
    if not source.is_file():
        return
    BROWSER_LOGO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination = BROWSER_LOGO_UPLOAD_DIR / f"browser-icon-00000000000000000001-legacy-{filename}"
    if not destination.exists():
        shutil.copy2(source, destination)


WEATHER_CONDITIONS = ("clear", "partly_cloudy", "overcast", "light_rain", "heavy_rain", "storm")
DEFAULT_LICENSE_TIERS = [
    {"min_rating": 0, "max_rating": 1499, "name": "Rookie", "color": "#64748b"},
    {"min_rating": 1500, "max_rating": 2499, "name": "Bronze", "color": "#b45309"},
    {"min_rating": 2500, "max_rating": 3999, "name": "Silver", "color": "#94a3b8"},
    {"min_rating": 4000, "max_rating": 5499, "name": "Gold", "color": "#ca8a04"},
    {"min_rating": 5500, "max_rating": 6999, "name": "Platinum", "color": "#0891b2"},
    {"min_rating": 7000, "max_rating": 8499, "name": "Diamond", "color": "#2563eb"},
    {"min_rating": 8500, "max_rating": 10000, "name": "Champ", "color": "#7c3aed"},
]


def weather_settings_from_value(value: dict | None) -> WeatherSettingsRead:
    value = value if isinstance(value, dict) else {}
    normalized = {}
    for condition in WEATHER_CONDITIONS:
        legacy_url = str(value.get(f"{condition}_url") or "").strip()
        for theme in ("light", "dark"):
            normalized[f"{condition}_{theme}_url"] = str(
                value.get(f"{condition}_{theme}_url") or legacy_url
            ).strip()
    return WeatherSettingsRead(**normalized)


async def get_weather_settings_value(session: AsyncSession) -> WeatherSettingsRead:
    setting = await session.get(AppSetting, WEATHER_SETTINGS_KEY)
    return weather_settings_from_value(setting.value if setting is not None else None)


def donation_settings_from_value(value: dict | None) -> DonationSettingsRead:
    if not isinstance(value, dict):
        return DonationSettingsRead()
    top_donations = []
    raw_donations = value.get("top_donations")
    if isinstance(raw_donations, list):
        for item in raw_donations[:5]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            amount = str(item.get("amount") or "").strip()
            if not name or not amount:
                continue
            top_donations.append(
                {
                    "name": name[:80],
                    "amount": amount[:40],
                    "message": str(item.get("message") or "").strip()[:120],
                }
            )
    return DonationSettingsRead(
        donation_url=str(value.get("donation_url") or "").strip(),
        top_donations=top_donations,
    )


async def get_donation_settings_value(session: AsyncSession) -> DonationSettingsRead:
    setting = await session.get(AppSetting, DONATION_SETTINGS_KEY)
    return donation_settings_from_value(setting.value if setting is not None else None)


def branding_settings_from_value(value: dict | None) -> BrandingSettingsRead:
    value = value if isinstance(value, dict) else {}
    metadata = site_metadata_from_file()
    return BrandingSettingsRead(
        light_logo_url=str(value.get("light_logo_url") or DEFAULT_LOGOS["light_logo_url"]),
        dark_logo_url=str(value.get("dark_logo_url") or DEFAULT_LOGOS["dark_logo_url"]),
        default_avatar_url=str(value.get("default_avatar_url") or DEFAULT_AVATAR_URL),
        browser_title=metadata["browser_title"],
        browser_description=metadata["browser_description"],
        browser_icon_url=DEFAULT_BROWSER_ICON_URL,
    )


async def get_branding_settings_value(session: AsyncSession) -> BrandingSettingsRead:
    setting = await session.get(AppSetting, BRANDING_SETTINGS_KEY)
    value = setting.value if setting is not None and isinstance(setting.value, dict) else {}
    migrate_legacy_browser_icon(value)
    branding = branding_settings_from_value(value)
    icon_path = latest_browser_icon_path()
    if icon_path is not None:
        return branding.model_copy(update={"browser_icon_url": browser_icon_file_url(icon_path)})
    legacy_url = str(value.get("browser_icon_url") or DEFAULT_BROWSER_ICON_URL)
    return branding.model_copy(update={"browser_icon_url": legacy_url})


def system_settings_from_value(value: dict | None) -> SystemSettingsRead:
    value = value if isinstance(value, dict) else {}
    raw_show_setups = value.get("show_setups_section", True)
    if isinstance(raw_show_setups, str):
        show_setups_section = raw_show_setups.strip().lower() not in {"", "0", "false", "no", "off"}
    else:
        show_setups_section = bool(raw_show_setups)
    try:
        requests_per_user = int(
            value.get(
                "requests_per_user_per_minute",
                value.get("rate_limit_per_minute", DEFAULT_REQUESTS_PER_USER_PER_MINUTE),
            )
        )
    except (TypeError, ValueError):
        requests_per_user = DEFAULT_REQUESTS_PER_USER_PER_MINUTE
    try:
        requests_per_ip = int(
            value.get(
                "requests_per_ip_per_minute",
                value.get("rate_limit_per_ip", requests_per_user),
            )
        )
    except (TypeError, ValueError):
        requests_per_ip = DEFAULT_REQUESTS_PER_IP_PER_MINUTE
    try:
        coefficient = float(
            value.get(
                "rating_change_coefficient",
                value.get("sr_change_coefficient", DEFAULT_RATING_CHANGE_COEFFICIENT),
            )
        )
    except (TypeError, ValueError):
        coefficient = DEFAULT_RATING_CHANGE_COEFFICIENT
    try:
        sr_per_race = float(value.get("sr_per_race", value.get("sr_finish_bonus", DEFAULT_SR_PER_RACE)))
    except (TypeError, ValueError):
        sr_per_race = DEFAULT_SR_PER_RACE
    return SystemSettingsRead(
        requests_per_user_per_minute=max(1, min(10000, requests_per_user)),
        requests_per_ip_per_minute=max(1, min(10000, requests_per_ip)),
        rating_change_coefficient=max(0.01, min(10, coefficient)),
        sr_per_race=max(0, min(100, sr_per_race)),
        show_setups_section=show_setups_section,
    )


async def get_system_settings_value(session: AsyncSession) -> SystemSettingsRead:
    setting = await session.get(AppSetting, SYSTEM_SETTINGS_KEY)
    return system_settings_from_value(setting.value if setting is not None else None)


def news_settings_from_value(value: dict | None) -> NewsSettingsRead:
    value = value if isinstance(value, dict) else {}
    try:
        auto_rotate_seconds = int(value.get("auto_rotate_seconds", DEFAULT_NEWS_AUTO_ROTATE_SECONDS))
    except (TypeError, ValueError):
        auto_rotate_seconds = DEFAULT_NEWS_AUTO_ROTATE_SECONDS
    try:
        manual_pause_seconds = int(value.get("manual_pause_seconds", DEFAULT_NEWS_MANUAL_PAUSE_SECONDS))
    except (TypeError, ValueError):
        manual_pause_seconds = DEFAULT_NEWS_MANUAL_PAUSE_SECONDS
    return NewsSettingsRead(
        auto_rotate_seconds=max(5, min(3600, auto_rotate_seconds)),
        manual_pause_seconds=max(0, min(3600, manual_pause_seconds)),
    )


async def get_news_settings_value(session: AsyncSession) -> NewsSettingsRead:
    setting = await session.get(AppSetting, NEWS_SETTINGS_KEY)
    return news_settings_from_value(setting.value if setting is not None else None)


async def load_runtime_settings(session: AsyncSession) -> SystemSettingsRead:
    setting = await session.get(AppSetting, SYSTEM_SETTINGS_KEY)
    value = system_settings_from_value(setting.value if setting is not None else None)
    normalized_value = value.model_dump()
    if setting is None:
        session.add(AppSetting(key=SYSTEM_SETTINGS_KEY, value=normalized_value))
        await session.commit()
    elif setting.value != normalized_value:
        setting.value = normalized_value
        await session.commit()
    set_request_limits(value.requests_per_user_per_minute, value.requests_per_ip_per_minute)
    return value


def license_settings_from_value(value: dict | None) -> LicenseSettingsRead:
    raw_tiers = value.get("tiers") if isinstance(value, dict) else []
    tiers = []
    for index, default in enumerate(DEFAULT_LICENSE_TIERS):
        item = raw_tiers[index] if isinstance(raw_tiers, list) and index < len(raw_tiers) and isinstance(raw_tiers[index], dict) else {}
        name = str(item.get("name") or default["name"]).strip()[:30] or default["name"]
        color = str(item.get("color") or default["color"]).strip()
        if not color.startswith("#") or len(color) != 7:
            color = default["color"]
        tiers.append({**default, "name": name, "color": color})
    return LicenseSettingsRead(tiers=tiers)


async def get_license_settings_value(session: AsyncSession) -> LicenseSettingsRead:
    setting = await session.get(AppSetting, LICENSE_SETTINGS_KEY)
    return license_settings_from_value(setting.value if setting is not None else None)


@router.get("/donations", response_model=DonationSettingsRead)
@limiter.limit("600/minute")
async def get_donation_settings(request: Request, session: AsyncSession = Depends(get_session)):
    return await get_donation_settings_value(session)


@router.patch("/donations", response_model=DonationSettingsRead)
@limiter.limit("20/minute")
async def update_donation_settings(
    payload: DonationSettingsUpdate,
    request: Request,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    value = {
        "donation_url": payload.donation_url.strip(),
        "top_donations": [item.model_dump() for item in payload.top_donations],
    }
    setting = await session.get(AppSetting, DONATION_SETTINGS_KEY)
    if setting is None:
        setting = AppSetting(key=DONATION_SETTINGS_KEY, value=value)
        session.add(setting)
    else:
        setting.value = value
    await session.commit()
    return donation_settings_from_value(value)


@router.get("/branding", response_model=BrandingSettingsRead)
@limiter.limit("600/minute")
async def get_branding_settings(request: Request, session: AsyncSession = Depends(get_session)):
    return await get_branding_settings_value(session)


@router.patch("/branding", response_model=BrandingSettingsRead)
@limiter.limit("20/minute")
async def update_branding_settings(
    payload: BrandingSettingsUpdate,
    request: Request,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    current = site_metadata_from_file()
    browser_title = payload.browser_title.strip()[:120] or current["browser_title"]
    browser_description = (
        current["browser_description"]
        if payload.browser_description is None
        else payload.browser_description.strip()[:320]
    )
    write_site_metadata(browser_title, browser_description)
    return await get_branding_settings_value(session)


@router.get("/branding/browser-icon")
@limiter.limit("600/minute")
async def get_browser_icon(request: Request, session: AsyncSession = Depends(get_session)):
    await get_branding_settings_value(session)
    icon_path = latest_browser_icon_path()
    if icon_path is None:
        raise HTTPException(status_code=404, detail="Browser icon is not configured")
    return FileResponse(
        icon_path,
        headers={"Cache-Control": "no-cache, max-age=0, must-revalidate"},
    )


@router.get("/weather", response_model=WeatherSettingsRead)
@limiter.limit("600/minute")
async def get_weather_settings(request: Request, session: AsyncSession = Depends(get_session)):
    return await get_weather_settings_value(session)


@router.post("/weather/{condition}/{theme}/upload", response_model=WeatherSettingsRead)
@limiter.limit("30/minute")
async def upload_weather_image(
    condition: Literal["clear", "partly_cloudy", "overcast", "light_rain", "heavy_rain", "storm"],
    theme: Literal["light", "dark"],
    request: Request,
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    extension = ALLOWED_LOGO_MEDIA_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(status_code=415, detail="Only PNG, JPG, WEBP and GIF files are allowed")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(data) > settings.max_logo_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File is larger than {settings.max_logo_upload_mb} MB")

    WEATHER_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = WEATHER_UPLOAD_DIR / f"{condition}-{theme}-{uuid4().hex}{extension}"
    path.write_bytes(data)
    current = await get_weather_settings_value(session)
    value = current.model_dump()
    value[f"{condition}_{theme}_url"] = f"/api/uploads/weather/{path.name}"
    setting = await session.get(AppSetting, WEATHER_SETTINGS_KEY)
    if setting is None:
        session.add(AppSetting(key=WEATHER_SETTINGS_KEY, value=value))
    else:
        setting.value = value
    await session.commit()
    return weather_settings_from_value(value)


@router.post("/branding/{theme}/upload", response_model=BrandingSettingsRead)
@limiter.limit("10/minute")
async def upload_branding_logo(
    theme: Literal["light", "dark", "default-avatar", "browser-icon"],
    request: Request,
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    extension = ALLOWED_LOGO_MEDIA_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(status_code=415, detail="Only PNG, JPG, WEBP and GIF files are allowed")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(data) > settings.max_logo_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File is larger than {settings.max_logo_upload_mb} MB")

    if theme == "browser-icon":
        BROWSER_LOGO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        uploaded_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = BROWSER_LOGO_UPLOAD_DIR / f"browser-icon-{uploaded_at}-{uuid4().hex}{extension}"
    else:
        LOGO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        path = LOGO_UPLOAD_DIR / f"{theme}-{uuid4().hex}{extension}"
    path.write_bytes(data)

    current = await get_branding_settings_value(session)
    value = current.model_dump()
    setting_key = {
        "default-avatar": "default_avatar_url",
        "browser-icon": "browser_icon_url",
    }.get(theme, f"{theme}_logo_url")
    value[setting_key] = browser_icon_file_url(path) if theme == "browser-icon" else f"/api/uploads/logos/{path.name}"
    setting = await session.get(AppSetting, BRANDING_SETTINGS_KEY)
    if setting is None:
        session.add(AppSetting(key=BRANDING_SETTINGS_KEY, value=value))
    else:
        setting.value = value
    await session.commit()
    return await get_branding_settings_value(session)


@router.get("/system", response_model=SystemSettingsRead)
@limiter.limit("600/minute")
async def get_system_settings(request: Request, session: AsyncSession = Depends(get_session)):
    return await get_system_settings_value(session)


@router.get("/news", response_model=NewsSettingsRead)
@limiter.limit("600/minute")
async def get_news_settings(request: Request, session: AsyncSession = Depends(get_session)):
    return await get_news_settings_value(session)


@router.patch("/news", response_model=NewsSettingsRead)
@limiter.limit("20/minute")
async def update_news_settings(
    payload: NewsSettingsUpdate,
    request: Request,
    _: User = Depends(require_news_editor),
    session: AsyncSession = Depends(get_session),
):
    value = payload.model_dump()
    setting = await session.get(AppSetting, NEWS_SETTINGS_KEY)
    if setting is None:
        session.add(AppSetting(key=NEWS_SETTINGS_KEY, value=value))
    else:
        setting.value = value
    await session.commit()
    return news_settings_from_value(value)


@router.patch("/system", response_model=SystemSettingsRead)
@limiter.limit("20/minute")
async def update_system_settings(
    payload: SystemSettingsUpdate,
    request: Request,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    value = {
        "requests_per_user_per_minute": payload.requests_per_user_per_minute,
        "requests_per_ip_per_minute": payload.requests_per_ip_per_minute or payload.requests_per_user_per_minute,
        "rating_change_coefficient": payload.rating_change_coefficient,
        "sr_per_race": payload.sr_per_race,
        "show_setups_section": payload.show_setups_section,
    }
    setting = await session.get(AppSetting, SYSTEM_SETTINGS_KEY)
    if setting is None:
        session.add(AppSetting(key=SYSTEM_SETTINGS_KEY, value=value))
    else:
        setting.value = value
    normalized = system_settings_from_value(value)
    set_request_limits(normalized.requests_per_user_per_minute, normalized.requests_per_ip_per_minute)
    await session.flush()
    await recalculate_all_ratings(session)
    await session.commit()
    return normalized


@router.get("/licenses", response_model=LicenseSettingsRead)
@limiter.limit("600/minute")
async def get_license_settings(request: Request, session: AsyncSession = Depends(get_session)):
    return await get_license_settings_value(session)


@router.patch("/licenses", response_model=LicenseSettingsRead)
@limiter.limit("20/minute")
async def update_license_settings(
    payload: LicenseSettingsUpdate,
    request: Request,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    value = {"tiers": [item.model_dump() for item in payload.tiers]}
    setting = await session.get(AppSetting, LICENSE_SETTINGS_KEY)
    if setting is None:
        setting = AppSetting(key=LICENSE_SETTINGS_KEY, value=value)
        session.add(setting)
    else:
        setting.value = value
    await session.commit()
    return license_settings_from_value(value)
