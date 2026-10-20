import unittest
from datetime import datetime, timezone

from app.models import PilotRoleBadge, PilotRoleDisplayMode, User
from app.routers.hall_of_fame import empty_stats, pilot_payload


def make_pilot(show_pilot_roles: bool = True) -> User:
    now = datetime(2026, 10, 5, tzinfo=timezone.utc)
    role = PilotRoleBadge(
        id=10,
        name="Победитель BMRL CHAMPIONSHIP 1",
        image_url=None,
        display_mode=PilotRoleDisplayMode.text,
        border_color="#ffd500",
        created_at=now,
        updated_at=now,
    )
    return User(
        id=7,
        login="pilot",
        first_name="Test",
        last_name="Pilot",
        nickname="Tester",
        pilot_number=77,
        country="Russia",
        sr=5.0,
        rating=1000,
        rating_race_count=0,
        game_ratings={},
        exclude_from_rer=False,
        avatar_color="#1652d8",
        show_pilot_roles=show_pilot_roles,
        pilot_roles=[role],
    )


class HallOfFameRolesTest(unittest.TestCase):
    def test_pilot_roles_are_part_of_the_standings_row(self):
        payload = pilot_payload(make_pilot(), "Team", "TMX", empty_stats())

        self.assertEqual([role.name for role in payload.pilot_roles], ["Победитель BMRL CHAMPIONSHIP 1"])
        self.assertEqual(payload.pilot_roles[0].border_color, "#ffd500")

    def test_hidden_roles_stay_hidden(self):
        payload = pilot_payload(make_pilot(show_pilot_roles=False), None, None, empty_stats())

        self.assertEqual(payload.pilot_roles, [])


if __name__ == "__main__":
    unittest.main()
