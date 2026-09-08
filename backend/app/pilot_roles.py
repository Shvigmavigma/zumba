def pilot_roles_payload(user) -> list[dict]:
    return [
        {
            "id": role.id,
            "name": role.name,
            "image_url": role.image_url,
            "display_mode": role.display_mode,
            "border_color": role.border_color,
        }
        for role in (getattr(user, "pilot_roles", None) or [])
    ]
