import unittest

from pydantic import ValidationError

from app.race_assets import DEFAULT_ACC_CAR_MODEL_IDS, DEFAULT_RACE_ASSETS, normalize_race_assets
from app.routers.races import acc_driver_category_for_user, acc_forced_car_model, acc_line_car_model, race_average_lap_ms
from app.schemas import RaceRegisterRequest, TeamRaceRegisterRequest


class AccEntrylistTest(unittest.TestCase):
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
