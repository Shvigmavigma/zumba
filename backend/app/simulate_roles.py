"""Seed a repeatable role-display scenario for every pilot account."""

import asyncio
import json

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionLocal
from app.models import PilotRoleBadge, PilotRoleDisplayMode, Role, User


SIMULATION_ROLES = (
    ("[SIM] Гонщик сезона", PilotRoleDisplayMode.text, None, "#2563eb"),
    ("[SIM] Лучший новичок", PilotRoleDisplayMode.text, None, "#16a34a"),
    (
        "[SIM] Длинная роль для проверки подиума и таблицы результатов",
        PilotRoleDisplayMode.text,
        None,
        "#db2777",
    ),
    ("[SIM] Символ скорости", PilotRoleDisplayMode.image, "/assets/bmrl-logo-nav.png", "#f59e0b"),
    ("[SIM] Медаль лидера", PilotRoleDisplayMode.image, "/assets/team-avatar-template.jpg", "#9333ea"),
    ("[SIM] Значок команды", PilotRoleDisplayMode.image, "/assets/weather/clear.png", "#0891b2"),
    (
        "[SIM] Чемпион сезона",
        PilotRoleDisplayMode.text_image,
        "/assets/bmrl-logo-nav.png",
        "#eab308",
    ),
    (
        "[SIM] Победитель этапа",
        PilotRoleDisplayMode.text_image,
        "/assets/team-avatar-template.jpg",
        "#ea580c",
    ),
    (
        "[SIM] Пилот зрительских симпатий",
        PilotRoleDisplayMode.text_image,
        "/assets/weather/storm.png",
        "#06b6d4",
    ),
)


async def run() -> dict[str, int]:
    async with SessionLocal() as session:
        role_by_name = {
            role.name: role
            for role in (
                await session.scalars(
                    select(PilotRoleBadge).where(
                        PilotRoleBadge.name.in_([item[0] for item in SIMULATION_ROLES])
                    )
                )
            ).all()
        }

        created = 0
        roles: list[PilotRoleBadge] = []
        for name, display_mode, image_url, border_color in SIMULATION_ROLES:
            role = role_by_name.get(name)
            if role is None:
                role = PilotRoleBadge(
                    name=name,
                    display_mode=display_mode,
                    image_url=image_url,
                    border_color=border_color,
                )
                session.add(role)
                created += 1
            else:
                # Keep a rerun deterministic if an earlier run was interrupted.
                role.display_mode = display_mode
                role.image_url = image_url
                role.border_color = border_color
            roles.append(role)

        await session.flush()
        pilots = list(
            (
                await session.scalars(
                    select(User)
                    .where(User.role == Role.pilot)
                    .options(selectinload(User.pilot_roles))
                    .order_by(User.id)
                )
            ).all()
        )

        assigned = 0
        role_ids = {role.id for role in roles}
        for pilot in pilots:
            current_ids = {role.id for role in pilot.pilot_roles}
            missing = role_ids - current_ids
            if missing:
                pilot.pilot_roles = [*pilot.pilot_roles, *(role for role in roles if role.id in missing)]
                assigned += len(missing)

        await session.commit()
        return {
            "roles_created": created,
            "simulation_roles": len(roles),
            "pilots_targeted": len(pilots),
            "assignments_added": assigned,
        }


def main() -> None:
    print(json.dumps(asyncio.run(run()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
