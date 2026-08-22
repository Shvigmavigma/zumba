from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.deps import require_admin
from app.models import AppSetting, User
from app.rate_limit import limiter, set_requests_per_user_per_minute
from app.schemas import BrandingSettingsRead, DonationSettingsRead, DonationSettingsUpdate, LicenseSettingsRead, LicenseSettingsUpdate, SystemSettingsRead, SystemSettingsUpdate


router = APIRouter()
settings = get_settings()

DONATION_SETTINGS_KEY = "donation_settings"
LICENSE_SETTINGS_KEY = "license_settings"
BRANDING_SETTINGS_KEY = "branding_settings"
SYSTEM_SETTINGS_KEY = "system_settings"
LOGO_UPLOAD_DIR = Path(settings.upload_dir) / "logos"
DEFAULT_LOGOS = {
    "light_logo_url": "/assets/bmrl-logo-light-cutout.png",
    "dark_logo_url": "/assets/bmrl-logo-dark-cutout.png",
}
DEFAULT_AVATAR_URL = "/assets/avatar-template.jpg"
DEFAULT_REQUESTS_PER_USER_PER_MINUTE = 1200
DEFAULT_RATING_CHANGE_COEFFICIENT = 1.5
DEFAULT_SR_PER_RACE = 0.3
# Kept as an import-compatible alias for older callers.
DEFAULT_SR_CHANGE_COEFFICIENT = DEFAULT_RATING_CHANGE_COEFFICIENT
ALLOWED_LOGO_MEDIA_TYPES = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
DEFAULT_LICENSE_TIERS = [
    {"min_rating": 0, "max_rating": 1499, "name": "Rookie", "color": "#64748b"},
    {"min_rating": 1500, "max_rating": 2499, "name": "Bronze", "color": "#b45309"},
    {"min_rating": 2500, "max_rating": 3999, "name": "Silver", "color": "#94a3b8"},
    {"min_rating": 4000, "max_rating": 5499, "name": "Gold", "color": "#ca8a04"},
    {"min_rating": 5500, "max_rating": 6999, "name": "Platinum", "color": "#0891b2"},
    {"min_rating": 7000, "max_rating": 8499, "name": "Diamond", "color": "#2563eb"},
    {"min_rating": 8500, "max_rating": 10000, "name": "Champ", "color": "#7c3aed"},
]


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
    return BrandingSettingsRead(
        light_logo_url=str(value.get("light_logo_url") or DEFAULT_LOGOS["light_logo_url"]),
        dark_logo_url=str(value.get("dark_logo_url") or DEFAULT_LOGOS["dark_logo_url"]),
        default_avatar_url=str(value.get("default_avatar_url") or DEFAULT_AVATAR_URL),
    )


async def get_branding_settings_value(session: AsyncSession) -> BrandingSettingsRead:
    setting = await session.get(AppSetting, BRANDING_SETTINGS_KEY)
    return branding_settings_from_value(setting.value if setting is not None else None)


def system_settings_from_value(value: dict | None) -> SystemSettingsRead:
    value = value if isinstance(value, dict) else {}
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
        rating_change_coefficient=max(0.01, min(10, coefficient)),
        sr_per_race=max(0, min(100, sr_per_race)),
    )


async def get_system_settings_value(session: AsyncSession) -> SystemSettingsRead:
    setting = await session.get(AppSetting, SYSTEM_SETTINGS_KEY)
    return system_settings_from_value(setting.value if setting is not None else None)


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
    set_requests_per_user_per_minute(value.requests_per_user_per_minute)
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


@router.post("/branding/{theme}/upload", response_model=BrandingSettingsRead)
@limiter.limit("10/minute")
async def upload_branding_logo(
    theme: Literal["light", "dark", "default-avatar"],
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

    LOGO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = LOGO_UPLOAD_DIR / f"{theme}-{uuid4().hex}{extension}"
    path.write_bytes(data)

    current = await get_branding_settings_value(session)
    value = current.model_dump()
    setting_key = "default_avatar_url" if theme == "default-avatar" else f"{theme}_logo_url"
    value[setting_key] = f"/api/uploads/logos/{path.name}"
    setting = await session.get(AppSetting, BRANDING_SETTINGS_KEY)
    if setting is None:
        session.add(AppSetting(key=BRANDING_SETTINGS_KEY, value=value))
    else:
        setting.value = value
    await session.commit()
    return branding_settings_from_value(value)


@router.get("/system", response_model=SystemSettingsRead)
@limiter.limit("600/minute")
async def get_system_settings(request: Request, session: AsyncSession = Depends(get_session)):
    return await get_system_settings_value(session)


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
        "rating_change_coefficient": payload.rating_change_coefficient,
        "sr_per_race": payload.sr_per_race,
    }
    setting = await session.get(AppSetting, SYSTEM_SETTINGS_KEY)
    if setting is None:
        session.add(AppSetting(key=SYSTEM_SETTINGS_KEY, value=value))
    else:
        setting.value = value
    await session.commit()
    normalized = system_settings_from_value(value)
    set_requests_per_user_per_minute(normalized.requests_per_user_per_minute)
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
