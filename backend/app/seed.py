from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Banner, BannerPosition, Role, User, UserStatus
from app.security import hash_password


async def seed_defaults(session: AsyncSession) -> None:
    settings = get_settings()

    admin = await session.scalar(select(User).where(User.login == settings.admin_login))
    if admin is None:
        session.add(
            User(
                login=settings.admin_login,
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                first_name="System",
                last_name="Admin",
                nickname="Admin",
                pilot_number=1,
                country="Global",
                sr=30.0,
                discord=None,
                steam_id="admin-steam",
                role=Role.admin,
                status=UserStatus.active,
                avatar_color="#ef4444",
            )
        )

    default_banners = {
        BannerPosition.top: ("/assets/banner-top.svg", "#"),
        BannerPosition.bottom: ("/assets/banner-bottom.svg", "#"),
        BannerPosition.left: ("/assets/banner-side.svg", "#"),
        BannerPosition.right: ("/assets/banner-side.svg", "#"),
    }
    for position, (image_url, link_url) in default_banners.items():
        exists = await session.scalar(select(Banner).where(Banner.position == position))
        if exists is None:
            session.add(Banner(position=position, image_url=image_url, link_url=link_url))

    await session.commit()

