import unittest

from app.routers.app_settings import DEFAULT_LOGOS, branding_settings_from_value


class BrandingSettingsTest(unittest.TestCase):
    def test_defaults_and_independent_theme_values(self):
        self.assertEqual(branding_settings_from_value(None).model_dump(), DEFAULT_LOGOS)
        self.assertEqual(
            branding_settings_from_value({"light_logo_url": "/custom-light.png"}).model_dump(),
            {"light_logo_url": "/custom-light.png", "dark_logo_url": DEFAULT_LOGOS["dark_logo_url"]},
        )


if __name__ == "__main__":
    unittest.main()
