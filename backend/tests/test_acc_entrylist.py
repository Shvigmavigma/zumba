import unittest
from types import SimpleNamespace

from pydantic import ValidationError

from app.race_assets import DEFAULT_ACC_CAR_MODEL_IDS, DEFAULT_RACE_ASSETS, normalize_race_assets, preserve_track_metadata
from app.routers.races import acc_best_lap_map, acc_driver_category_for_user, acc_forced_car_model, acc_line_car_model, build_acc_results_payload, race_average_lap_ms
from app.schemas import RaceRegisterRequest, TeamRaceRegisterRequest
from app.services import build_rating_changes, rating_positions


class AccEntrylistTest(unittest.TestCase):
    def test_results_skip_zero_lap_rows_and_match_active_profiles(self):
        def line(player_id, name, laps, *, race_number=7, best_lap=95000, total_time=1900000):
            return {
                "car": {"raceNumber": race_number, "carModel": 30},
                "currentDriver": {"playerId": player_id, "firstName": name, "lastName": "Driver"},
                "timing": {"lapCount": laps, "bestLap": best_lap, "totalTime": total_time},
            }

        registered_user = SimpleNamespace(
            id=1,
            steam_id="76561198000000001",
            login="registered",
            nickname="Registered",
            exclude_from_rer=False,
            team_id=None,
        )
        guest_user = SimpleNamespace(
            id=2,
            steam_id="76561198000000002",
            login="guest",
            nickname="Guest",
            exclude_from_rer=False,
            team_id=None,
        )
        race = SimpleNamespace(has_qualification=True, track="Silverstone")
        qualification = {"sessionType": "Q", "sessionResult": {"leaderBoardLines": [line("S76561198000000001", "Registered", 3), line("S76561198000000002", "DNS", 0)]}}
        results = {"sessionType": "R", "trackName": "silverstone", "sessionResult": {"leaderBoardLines": [line("S76561198000000001", "Registered", 20), line("S76561198000000002", "Guest", 18), line("S76561198000000003", "DNS", 0)]}}

        payload = build_acc_results_payload(
            race,
            qualification,
            results,
            [(SimpleNamespace(pilot_number=7), registered_user)],
            {"76561198000000002": guest_user},
        )

        self.assertEqual([row["driver_name"] for row in payload["rows"]], ["Registered Driver", "Guest Driver"])
        self.assertEqual([row["user_id"] for row in payload["rows"]], [1, 2])
        self.assertEqual(payload["rows"][0]["qualification_position"], 1)
        self.assertEqual(acc_best_lap_map(qualification), {"76561198000000001": {"qualification_position": 1, "qualification_best_lap_ms": 95000}})

    def test_rating_positions_compact_places_when_guests_are_not_eligible(self):
        rows = [
            {"user_id": 1, "position": 1, "finish_ms": 1000},
            {"user_id": 2, "position": 3, "finish_ms": 1200},
            {"user_id": 3, "position": 5, "finish_ms": 1400},
        ]
        self.assertEqual(rating_positions(rows), {1: 1.0, 2: 2.0, 3: 3.0})

    def test_rer_awards_fixed_positive_bonuses_to_top_eight(self):
        rows = [{"user_id": index, "position": index, "finish_ms": index * 1000} for index in range(1, 10)]
        users = {
            index: SimpleNamespace(
                id=index,
                exclude_from_rer=False,
                rating=9000 if index == 1 else 1000,
                game_ratings={"ACC": {"rating": 9000 if index == 1 else 1000, "race_count": 20}},
                rating_race_count=20,
            )
            for index in range(1, 10)
        }

        changes, _ = build_rating_changes(rows, users, "ACC")
        deltas = {change["position"]: change["delta"] for change in changes}

        self.assertEqual([deltas[float(position)] for position in range(1, 9)], [100, 90, 80, 70, 60, 50, 40, 30])
        self.assertGreaterEqual(deltas[8.0], 0)
        self.assertGreaterEqual(deltas[9.0], -100)
        self.assertLessEqual(deltas[9.0], 100)

    def test_average_lap_ignores_missing_zero_fields(self):
        results = {
            "rows": [
                {"finish_ms": 1900000, "lap_count": 20, "best_lap_ms": 95000, "qualification_best_lap_ms": 0},
                {"finish_ms": 1920000, "lap_count": 20, "best_lap_ms": 96000, "status": "missing"},
                {"finish_ms": None, "lap_count": 0, "best_lap_ms": 100000},
            ]
        }
        self.assertEqual(race_average_lap_ms(results), 97500)

    def test_driver_category_uses_the_selected_game_license(self):
        tiers = [
            {"min_rating": 0, "max_rating": 1499, "name": "Rookie"},
            {"min_rating": 1500, "max_rating": 2499, "name": "Bronze"},
            {"min_rating": 2500, "max_rating": 3999, "name": "Silver"},
            {"min_rating": 4000, "max_rating": 5499, "name": "Gold"},
            {"min_rating": 5500, "max_rating": 6999, "name": "Platinum"},
            {"min_rating": 7000, "max_rating": 8499, "name": "Diamond"},
            {"min_rating": 8500, "max_rating": 10000, "name": "Champ"},
        ]
        expected = {1000: 0, 2000: 0, 3000: 1, 4500: 2, 6000: 3, 7500: 3, 9000: 3}
        for rating, category in expected.items():
            user = {"rating": 1000, "game_ratings": {"ACC": {"rating": rating}}}
            self.assertEqual(acc_driver_category_for_user(user, "ACC", tiers), category)

        self.assertEqual(
            acc_driver_category_for_user(
                {"rating": 9000, "game_ratings": {"ACC": {"rating": 1000}, "AC": {"rating": 3000}}},
                "AC",
                tiers,
            ),
            1,
        )

    def test_default_mapping_contains_the_acc_ids(self):
        config = normalize_race_assets({"tracks": [], "classes": [], "games": {}})
        self.assertEqual(config.car_model_ids, DEFAULT_ACC_CAR_MODEL_IDS)
        self.assertEqual(config.car_model_ids["Porsche 991 GT3 R"], 0)
        self.assertEqual(config.car_model_ids["Ford Mustang GT3"], 36)
        self.assertEqual(config.car_model_ids["Porsche 935"], 86)

    def test_expected_average_lap_is_preserved_when_track_is_renamed(self):
        previous = normalize_race_assets({"tracks": ["Monza"], "expected_average_lap_ms": {"Monza": 108500}, "games": {}})
        incoming = normalize_race_assets({"tracks": ["Monza 2024"], "games": {}})
        saved = preserve_track_metadata(previous.games["ACC"], incoming.games["ACC"])
        self.assertEqual(saved.expected_average_lap_ms, {"Monza 2024": 108500})

    def test_track_image_crop_is_preserved_when_track_is_renamed(self):
        previous = normalize_race_assets({
            "tracks": ["Monza"],
            "track_images": {"Monza": "/api/uploads/track-images/monza.jpg"},
            "track_image_crops": {"Monza": {"zoom": 1.8, "x": 25, "y": 70}},
            "games": {},
        })
        incoming = normalize_race_assets({"tracks": ["Monza GP"], "games": {}})
        saved = preserve_track_metadata(previous.games["ACC"], incoming.games["ACC"])
        self.assertEqual(saved.track_image_crops["Monza GP"].model_dump(), {"zoom": 1.8, "x": 25, "y": 70})

    def test_track_image_crop_bounds_are_validated(self):
        with self.assertRaises(ValidationError):
            normalize_race_assets({
                "tracks": ["Monza"],
                "track_image_crops": {"Monza": {"zoom": 4, "x": 50, "y": 50}},
                "games": {},
            })

    def test_admin_mapping_overrides_a_model_id(self):
        custom = {"BMW M4 GT3": 99}
        self.assertEqual(acc_forced_car_model("BMW M4 GT3", custom), 99)
        self.assertEqual(acc_forced_car_model("BMW M4 GT3 2021", custom), 30)

    def test_default_race_asset_cars_have_acc_ids(self):
        cars = [car for asset_class in DEFAULT_RACE_ASSETS["classes"] for car in asset_class["cars"]]
        self.assertFalse([car for car in cars if acc_forced_car_model(car) < 0])

    def test_result_car_model_accepts_nested_and_flat_ids(self):
        self.assertEqual(acc_line_car_model({"car": {"carModel": 30}}), 30)
        self.assertEqual(acc_line_car_model({"carModel": "31"}), 31)
        self.assertEqual(acc_line_car_model({"forcedCarModel": 32}), 32)

    def test_race_registration_rejects_zero_number(self):
        with self.assertRaises(ValidationError):
            RaceRegisterRequest(car_model="30", pilot_number=0)
        with self.assertRaises(ValidationError):
            TeamRaceRegisterRequest(car_model="30", race_number=0, drivers=[{"user_id": 1}])


if __name__ == "__main__":
    unittest.main()
