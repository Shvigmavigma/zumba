import unittest

from app.race_assets import DEFAULT_ACC_CAR_MODEL_IDS, DEFAULT_RACE_ASSETS, normalize_race_assets
from app.routers.races import acc_forced_car_model


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


if __name__ == "__main__":
    unittest.main()
