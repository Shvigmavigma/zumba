from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_admin
from app.models import AppSetting, User
from app.rate_limit import limiter
from app.schemas import DonationSettingsRead, DonationSettingsUpdate, LicenseSettingsRead, LicenseSettingsUpdate


router = APIRouter()

DONATION_SETTINGS_KEY = "donation_settings"
LICENSE_SETTINGS_KEY = "license_settings"
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
