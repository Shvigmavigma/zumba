import unittest

from app.routers.app_settings import DEFAULT_AVATAR_URL, DEFAULT_LOGOS, DEFAULT_RATING_CHANGE_COEFFICIENT, DEFAULT_REQUESTS_PER_USER_PER_MINUTE, DEFAULT_SR_PER_RACE, branding_settings_from_value, system_settings_from_value


class BrandingSettingsTest(unittest.TestCase):
    def test_defaults_and_independent_theme_values(self):
        self.assertEqual(
            branding_settings_from_value(None).model_dump(),
            {**DEFAULT_LOGOS, "default_avatar_url": DEFAULT_AVATAR_URL},
        )
        self.assertEqual(
            branding_settings_from_value({"light_logo_url": "/custom-light.png"}).model_dump(),
            {
                "light_logo_url": "/custom-light.png",
                "dark_logo_url": DEFAULT_LOGOS["dark_logo_url"],
                "default_avatar_url": DEFAULT_AVATAR_URL,
            },
        )

    def test_system_settings_are_normalized(self):
        self.assertEqual(
            system_settings_from_value(None).model_dump(),
            {
                "requests_per_user_per_minute": DEFAULT_REQUESTS_PER_USER_PER_MINUTE,
                "rating_change_coefficient": DEFAULT_RATING_CHANGE_COEFFICIENT,
                "sr_per_race": DEFAULT_SR_PER_RACE,
            },
        )
        normalized = system_settings_from_value({"rate_limit_per_minute": 0, "rating_change_coefficient": 99})
        self.assertEqual(normalized.requests_per_user_per_minute, 1)
        self.assertEqual(normalized.rating_change_coefficient, 10)
        self.assertEqual(normalized.sr_per_race, DEFAULT_SR_PER_RACE)

    def test_legacy_sr_coefficient_is_migrated_to_common_rating_coefficient(self):
        normalized = system_settings_from_value({"sr_change_coefficient": 2.5})
        self.assertEqual(normalized.rating_change_coefficient, 2.5)
        self.assertEqual(normalized.sr_per_race, DEFAULT_SR_PER_RACE)


if __name__ == "__main__":
    unittest.main()
