import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from app.models import PilotRoleDisplayMode
from app.routers.races import build_manual_results_payload, storable_results
from app.schemas import ManualResultsUpload


def pilot_with_role_badge() -> dict:
    """An entry of the race's grid as registration_to_json gives it: the role badge carries its dates."""
    assigned = datetime(2026, 10, 1, 18, 30, tzinfo=timezone.utc)
    return {
        "user_id": 7,
        "login": "pilot7",
        "nickname": "Pilot 7",
        "first_name": "",
        "last_name": "",
        "pilot_number": 77,
        "race_number": 77,
        "car_model": "Formula 4",
        "pilot_roles": [
            {
                "id": 1,
                "name": "Champion",
                "image_url": None,
                "display_mode": PilotRoleDisplayMode.text,
                "border_color": "#ffd500",
                "created_at": assigned,
                "updated_at": assigned,
            }
        ],
    }


class ResultsWithRoleBadgesTest(unittest.TestCase):
    def test_results_of_a_pilot_with_a_role_badge_can_be_stored(self) -> None:
        race = SimpleNamespace(game="AC", track="Red Bull Ring", has_qualification=True)
        payload = ManualResultsUpload(rows=[{"user_id": 7, "finish_ms": 4_557_618, "lap_count": 49, "best_lap_ms": 91_445}])

        results = storable_results(build_manual_results_payload(race, payload, [pilot_with_role_badge()]))

        stored = json.loads(json.dumps(results))
        role = stored["rows"][0]["pilot_roles"][0]
        self.assertEqual(role["name"], "Champion")
        self.assertEqual(role["display_mode"], "text")
        self.assertEqual(role["created_at"], "2026-10-01T18:30:00+00:00")

    def test_plain_results_are_stored_as_they_are(self) -> None:
        results = {"format": "manual", "rows": [{"user_id": 7, "finish_ms": 1, "best_sectors_ms": [1, None, 3], "gap_ms": None}]}

        self.assertEqual(storable_results(results), results)


if __name__ == "__main__":
    unittest.main()
