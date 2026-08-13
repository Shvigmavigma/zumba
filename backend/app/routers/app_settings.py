from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_admin
from app.models import AppSetting, User
from app.rate_limit import limiter
from app.schemas import DonationSettingsRead, DonationSettingsUpdate


router = APIRouter()

DONATION_SETTINGS_KEY = "donation_settings"


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
