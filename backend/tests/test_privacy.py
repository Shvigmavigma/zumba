import unittest
from types import SimpleNamespace

from pydantic import ValidationError

from app.config import get_settings
from app.device import set_device_cookie
from app.schemas import UserRegister


def registration_payload(**overrides):
    payload = {
        "login": "privacy-pilot",
        "email": "privacy@example.com",
        "password": "correct-horse-battery",
        "password_confirm": "correct-horse-battery",
        "first_name": "Privacy",
        "last_name": "Pilot",
        "nickname": "Privacy Pilot",
        "pilot_number": 123,
        "steam_auth_token": "opaque-registration-token",
        "data_processing_consent": True,
        "terms_accepted": True,
    }
    payload.update(overrides)
    return payload


class RecordingResponse:
    def __init__(self):
        self.cookie = None

    def set_cookie(self, *args, **kwargs):
        self.cookie = {"args": args, "kwargs": kwargs}


def request_for(hostname: str, scheme: str = "http", forwarded_proto: str = ""):
    return SimpleNamespace(
        headers={"x-forwarded-proto": forwarded_proto},
        url=SimpleNamespace(hostname=hostname, scheme=scheme),
    )


class PrivacyTest(unittest.TestCase):
    def test_registration_requires_processing_consent_and_terms(self):
        UserRegister(**registration_payload())

        with self.assertRaises(ValidationError):
            UserRegister(**registration_payload(data_processing_consent=False))
        with self.assertRaises(ValidationError):
            UserRegister(**registration_payload(terms_accepted=False))

    def test_production_device_cookie_is_secure_behind_tls_proxy(self):
        settings = get_settings()
        original_url = settings.public_base_url
        settings.public_base_url = "https://bmrl.site"
        try:
            response = RecordingResponse()
            set_device_cookie(response, "device-token", request_for("bmrl.site"))
            self.assertTrue(response.cookie["kwargs"]["secure"])
        finally:
            settings.public_base_url = original_url

    def test_device_cookie_stays_usable_on_local_http(self):
        response = RecordingResponse()
        set_device_cookie(response, "device-token", request_for("localhost"))
        self.assertFalse(response.cookie["kwargs"]["secure"])


if __name__ == "__main__":
    unittest.main()
