import unittest

from pydantic import ValidationError

from app.race_assets import DEFAULT_ACC_CAR_MODEL_IDS, DEFAULT_RACE_ASSETS, normalize_race_assets
from app.routers.races import acc_forced_car_model, acc_line_car_model
from app.schemas import RaceRegisterRequest, TeamRaceRegisterRequest


class AccEntrylistTest(unittest.TestCase):
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
