import asyncio
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Banner, BannerPosition, NewsItem, User


DEFAULT_BANNERS = {
    BannerPosition.top: ("/assets/banner-top.svg", "#"),
    BannerPosition.bottom: ("/assets/banner-bottom.svg", "#"),
    BannerPosition.left: ("/assets/banner-side.svg", "#"),
    BannerPosition.right: ("/assets/banner-side.svg", "#"),
}

DEFAULT_NEWS = [
    (
        "BMRL годовой сезон запущен",
        "Сетка заполнена чемпионатами, гонками и результатами за полный симуляционный год.",
        "/assets/banner-top.svg",
    ),
    (
        "Новые трассовые рекорды",
        "Во вкладке пилотов теперь можно смотреть лучшие круги по трассам и симуляторам.",
        "/assets/banner-side.svg",
    ),
    (
        "Командный рейтинг обновлен",
        "Команды получили плотную историю выступлений, штрафов, апелляций и голосований.",
        "/assets/banner-bottom.svg",
    ),
]


async def run() -> dict:
    async with SessionLocal() as session:
        settings = get_settings()
        admin = await session.scalar(select(User).where(User.login == settings.admin_login))
        admin_id = admin.id if admin else None

        for position, (image_url, link_url) in DEFAULT_BANNERS.items():
            banner = await session.scalar(select(Banner).where(Banner.position == position))
            if banner is None:
                session.add(Banner(position=position, image_url=image_url, link_url=link_url, updated_by=admin_id))
            else:
                banner.image_url = image_url
                banner.link_url = link_url
                banner.updated_by = admin_id

        await session.execute(delete(NewsItem))
        now = datetime.now(timezone.utc)
        for index, (title, body, image_url) in enumerate(DEFAULT_NEWS):
            session.add(
                NewsItem(
                    title=title,
                    body=body,
                    image_url=image_url,
                    is_published=True,
                    created_by=admin_id,
                    created_at=now - timedelta(hours=index),
                )
            )

        await session.commit()
        return {"banners": len(DEFAULT_BANNERS), "news": len(DEFAULT_NEWS)}


def main() -> None:
    print(json.dumps(asyncio.run(run()), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
