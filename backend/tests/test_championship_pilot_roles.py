import unittest
from datetime import datetime, timezone

from app.models import PilotRoleBadge, PilotRoleDisplayMode, Role, User, UserStatus
from app.routers.championships import user_payload
from app.schemas import PilotRoleRead, TeamMemberRead


def make_pilot_with_role() -> User:
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)
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
        role=Role.pilot,
        status=UserStatus.active,
        avatar_color="#1652d8",
        games=["ACC"],
        show_pilot_roles=True,
        pilot_roles=[role],
        created_at=now,
    )


class ChampionshipPilotRolesTest(unittest.TestCase):
    def test_registered_pilot_with_a_role_passes_the_response_schema(self):
        # The championship list failed with a 500 as soon as one registered
        # pilot held a role: the badge payload must satisfy the response schema.
        payload = user_payload(make_pilot_with_role(), "Team", "TMX")

        member = TeamMemberRead.model_validate(payload)

        self.assertEqual([role.name for role in member.pilot_roles], ["Победитель BMRL CHAMPIONSHIP 1"])
        self.assertEqual(member.pilot_roles[0].created_at, datetime(2026, 10, 6, tzinfo=timezone.utc))

    def test_admin_role_records_keep_their_timestamps(self):
        role = make_pilot_with_role().pilot_roles[0]

        self.assertEqual(PilotRoleRead.model_validate(role).created_at, role.created_at)


if __name__ == "__main__":
    unittest.main()
