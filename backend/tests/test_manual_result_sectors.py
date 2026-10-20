import unittest
from types import SimpleNamespace

from pydantic import ValidationError

from app.routers.races import build_manual_results_payload
from app.routers.users import row_best_laps
from app.schemas import ManualResultsUpload


def registered_pilot(user_id: int, number: int) -> dict:
    return {
        "user_id": user_id,
        "login": f"pilot{user_id}",
        "nickname": f"Pilot {user_id}",
        "first_name": "",
        "last_name": "",
        "pilot_number": number,
        "race_number": number,
        "car_model": "Formula 4",
    }


def ac_race() -> SimpleNamespace:
    return SimpleNamespace(game="AC", track="Red Bull Ring", has_qualification=True)


class ManualResultSectorsTest(unittest.TestCase):
    def test_sector_times_from_the_session_file_are_kept_with_the_row(self) -> None:
        payload = ManualResultsUpload(
            rows=[
                {
                    "user_id": 7,
                    "finish_ms": 4_557_618,
                    "lap_count": 49,
                    "best_lap_ms": 91_445,
                    "best_sectors_ms": [21_400, 37_700, 31_800],
                    "valid_laps": 49,
                    "qualification_best_sectors_ms": [21_300, None, 31_500],
                    "qualification_valid_laps": 5,
                }
            ]
        )

        row = build_manual_results_payload(ac_race(), payload, [registered_pilot(7, 77)])["rows"][0]

        self.assertEqual(row["best_sectors_ms"], [21_400, 37_700, 31_800])
        self.assertEqual(row["valid_laps"], 49)
        self.assertEqual(row["qualification_best_sectors_ms"], [21_300, None, 31_500])
        self.assertEqual(row["qualification_valid_laps"], 5)
        self.assertEqual(row["best_lap_ms"], 91_445)

    def test_a_row_without_sector_times_looks_as_before(self) -> None:
        payload = ManualResultsUpload(rows=[{"user_id": 7, "finish_ms": 4_557_618, "lap_count": 49, "best_lap_ms": 91_445}])

        row = build_manual_results_payload(ac_race(), payload, [registered_pilot(7, 77)])["rows"][0]

        for key in ("best_sectors_ms", "valid_laps", "qualification_best_sectors_ms", "qualification_valid_laps"):
            self.assertNotIn(key, row)

    def test_sector_times_that_cannot_be_lap_sectors_are_refused(self) -> None:
        for sectors in ([21_400, 37_700], [21_400, 37_700, 31_800, 100], [21_400, -5, 31_800], [0, 37_700, 31_800], [21_400, 37_700, 86_400_001]):
            with self.subTest(sectors=sectors), self.assertRaises(ValidationError):
                ManualResultsUpload(rows=[{"user_id": 7, "finish_ms": 1, "best_sectors_ms": sectors}])
        with self.assertRaises(ValidationError):
            ManualResultsUpload(rows=[{"user_id": 7, "finish_ms": 1, "valid_laps": -1}])

    def test_a_race_without_a_result_file_keeps_the_qualifying_lap_that_comes_with_the_row(self) -> None:
        payload = ManualResultsUpload(
            rows=[
                {"user_id": 7, "finish_ms": 4_557_618, "lap_count": 49, "best_lap_ms": 91_184, "qualification_best_lap_ms": 90_609},
                {"user_id": 8, "finish_ms": 4_560_000, "lap_count": 49, "best_lap_ms": 91_146},
            ]
        )

        rows = build_manual_results_payload(ac_race(), payload, [registered_pilot(7, 77), registered_pilot(8, 88)])["rows"]

        self.assertEqual(rows[0]["qualification_best_lap_ms"], 90_609)
        self.assertIsNone(rows[1]["qualification_best_lap_ms"])
        # The grid order is not worked out from these laps: championship points for pole stay as they were.
        self.assertIsNone(rows[0]["qualification_position"])

    def test_a_race_without_qualifying_keeps_no_qualifying_lap(self) -> None:
        race = SimpleNamespace(game="AC", track="Red Bull Ring", has_qualification=False)
        payload = ManualResultsUpload(rows=[{"user_id": 7, "finish_ms": 1, "qualification_best_lap_ms": 90_609}])

        row = build_manual_results_payload(race, payload, [registered_pilot(7, 77)])["rows"][0]

        self.assertIsNone(row["qualification_best_lap_ms"])

    def test_acc_qualifying_is_still_ranked_from_the_laps(self) -> None:
        race = SimpleNamespace(game="ACC", track="Silverstone", has_qualification=True)
        payload = ManualResultsUpload(
            rows=[
                {"user_id": 7, "finish_ms": 10, "qualification_best_lap_ms": 118_500},
                {"user_id": 8, "finish_ms": 20, "qualification_best_lap_ms": 118_037},
            ]
        )

        rows = build_manual_results_payload(race, payload, [registered_pilot(7, 77), registered_pilot(8, 88)])["rows"]

        self.assertEqual([row["qualification_position"] for row in rows], [2, 1])

    def test_laps_annulled_by_the_stewards_stay_with_the_row(self) -> None:
        payload = ManualResultsUpload(rows=[{"user_id": 7, "finish_ms": 4_557_618, "lap_count": 49, "best_lap_ms": 91_445, "laps_annulled": True}])

        row = build_manual_results_payload(ac_race(), payload, [registered_pilot(7, 77)])["rows"][0]

        self.assertIs(row["laps_annulled"], True)
        self.assertEqual(row["best_lap_ms"], 91_445)

    def test_a_pilot_s_own_records_leave_out_laps_the_stewards_annulled(self) -> None:
        kept = {"best_lap_ms": 91_445, "qualification_best_lap_ms": 90_609}

        self.assertEqual(list(row_best_laps(kept)), [("qualification", 90_609), ("race", 91_445)])
        self.assertEqual(list(row_best_laps({**kept, "laps_annulled": True})), [])
        self.assertEqual(list(row_best_laps({**kept, "laps_annulled": False})), [("qualification", 90_609), ("race", 91_445)])


if __name__ == "__main__":
    unittest.main()
