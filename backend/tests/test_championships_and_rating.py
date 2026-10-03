from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import TestCase

from app.models import ChampionshipScoringSystem, RaceStatus, TeamApplicationStatus
from app.routers.championships import build_standings
from app.schemas import ChampionshipCreate
from app.services import build_rating_changes


def pilot(user_id: int, pilot_number: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        login=f"pilot{user_id}",
        first_name="First",
        last_name="Last",
        nickname=f"Pilot {user_id}",
        pilot_number=pilot_number,
        team_id=None,
        avatar_color="#2563eb",
        avatar_url=None,
        exclude_from_rer=False,
        rating=1000,
        game_ratings={},
        sr=5.0,
        pilot_roles=[],
    )


class ChampionshipAndRatingTests(TestCase):
    def test_championship_registration_must_end_before_start(self):
        start = datetime(2026, 10, 10, tzinfo=timezone.utc)
        payload = {
            "name": "Test championship",
            "registration_start": start,
            "registration_end": start + timedelta(days=1),
            "championship_start": start + timedelta(days=1),
            "championship_end": start + timedelta(days=8),
            "classes": ["GT3"],
        }

        with self.assertRaises(ValueError):
            ChampionshipCreate(**payload)

    def test_championship_ties_use_results_before_pilot_number(self):
        first = pilot(1, 999)
        second = pilot(2, 1)
        registrations = [
            (SimpleNamespace(user_id=first.id, status=TeamApplicationStatus.approved, pilot_number=999), first, None, None),
            (SimpleNamespace(user_id=second.id, status=TeamApplicationStatus.approved, pilot_number=1), second, None, None),
        ]
        positions = [(1, 1), (2, 3), (4, 3)]
        stages = [
            SimpleNamespace(
                status=RaceStatus.finished,
                scoring_system=ChampionshipScoringSystem.fia,
                pole_bonus_enabled=False,
                results={"rows": [{"user_id": first.id, "position": first_position}, {"user_id": second.id, "position": second_position}]},
            )
            for first_position, second_position in positions
        ]

        standings = build_standings(SimpleNamespace(), stages, registrations)

        self.assertEqual([item["user_id"] for item in standings], [first.id, second.id])
        self.assertEqual(standings[0]["points"], standings[1]["points"])
        self.assertEqual(standings[0]["wins"], standings[1]["wins"])
        self.assertGreater(standings[0]["second_places"], standings[1]["second_places"])

    def test_rating_changes_are_bounded_balanced_and_can_reach_maximum(self):
        users = {
            user_id: SimpleNamespace(
                rating=1000,
                rating_race_count=0,
                game_ratings={"ACC": {"rating": 1000, "race_count": 0}},
                exclude_from_rer=False,
            )
            for user_id in range(1, 31)
        }
        rows = [{"user_id": user_id, "position": user_id, "finish_ms": user_id * 1000} for user_id in users]

        changes, _ = build_rating_changes(rows, users, "ACC", 1.0)

        self.assertEqual(sum(change["delta"] for change in changes), 0)
        self.assertLessEqual(max(change["delta"] for change in changes), 250)
        self.assertGreaterEqual(min(change["delta"] for change in changes), -250)

        maxed_users = {
            user_id: SimpleNamespace(
                rating=9990,
                rating_race_count=0,
                game_ratings={"ACC": {"rating": 9990, "race_count": 0}},
                exclude_from_rer=False,
            )
            for user_id in range(1, 9)
        }
        maxed_rows = [{"user_id": user_id, "position": user_id, "finish_ms": user_id * 1000} for user_id in maxed_users]
        maxed_changes, _ = build_rating_changes(maxed_rows, maxed_users, "ACC", 1.0)

        self.assertEqual(maxed_changes[0]["new_rating"], 10000)


if __name__ == "__main__":
    import unittest

    unittest.main()
