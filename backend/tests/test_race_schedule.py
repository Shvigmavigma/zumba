from datetime import datetime, timedelta, timezone
from unittest import TestCase

from app.models import RaceStatus
from app.routers.races import scheduled_race_status


class RaceScheduleTests(TestCase):
    def test_registration_window_and_race_time_are_independent(self):
        registration_start = datetime(2026, 8, 24, 10, tzinfo=timezone.utc)
        registration_end = registration_start + timedelta(days=2)
        race_time = registration_end + timedelta(days=1)

        self.assertEqual(scheduled_race_status(registration_start, registration_end, race_time, registration_start - timedelta(minutes=1)), RaceStatus.not_started)
        self.assertEqual(scheduled_race_status(registration_start, registration_end, race_time, registration_start + timedelta(hours=1)), RaceStatus.registration_open)
        self.assertEqual(scheduled_race_status(registration_start, registration_end, race_time, registration_end + timedelta(hours=1)), RaceStatus.not_started)
        self.assertEqual(scheduled_race_status(registration_start, registration_end, race_time, race_time), RaceStatus.ongoing)
