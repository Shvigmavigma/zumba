def pilot_roles_payload(user) -> list[dict]:
    if getattr(user, "show_pilot_roles", True) is False:
        return []
    return [
        {
            "id": role.id,
            "name": role.name,
            "image_url": role.image_url,
            "display_mode": role.display_mode,
            "border_color": role.border_color,
            "created_at": role.created_at,
            "updated_at": role.updated_at,
        }
        for role in (getattr(user, "pilot_roles", None) or [])
    ]
