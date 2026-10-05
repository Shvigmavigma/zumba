from datetime import datetime, time, timedelta, timezone
from unittest import TestCase

from pydantic import ValidationError

from app.models import RaceStatus
from app.routers.races import scheduled_race_status
from app.schemas import RaceCreate, RaceUpdate


class RaceScheduleTests(TestCase):
    def test_registration_window_and_race_time_are_independent(self):
        registration_start = datetime(2026, 8, 24, 10, tzinfo=timezone.utc)
        registration_end = registration_start + timedelta(days=2)
        race_time = registration_end + timedelta(days=1)

        self.assertEqual(scheduled_race_status(registration_start, registration_end, race_time, registration_start - timedelta(minutes=1)), RaceStatus.not_started)
        self.assertEqual(scheduled_race_status(registration_start, registration_end, race_time, registration_start + timedelta(hours=1)), RaceStatus.registration_open)
        self.assertEqual(scheduled_race_status(registration_start, registration_end, race_time, registration_end + timedelta(hours=1)), RaceStatus.not_started)
        self.assertEqual(scheduled_race_status(registration_start, registration_end, race_time, race_time), RaceStatus.ongoing)

    def test_session_times_are_parsed_as_local_clock_times(self):
        update = RaceUpdate.model_validate({"practice_start_time": "19:00", "race_session_end_time": "20:15"})

        self.assertEqual(update.practice_start_time, time(19, 0))
        self.assertEqual(update.race_session_end_time, time(20, 15))

    def test_briefing_and_required_pit_stops_round_trip_through_race_schemas(self):
        update = RaceUpdate.model_validate({
            "briefing_start_time": "19:00",
            "briefing_end_time": "19:15",
            "required_pit_stops": 2,
        })
        created = RaceCreate.model_validate({
            "name": "Test race",
            "description": "",
            "server_link": "",
            "registration_start": "2026-10-01T10:00:00Z",
            "datetime_start": "2026-10-01T12:00:00Z",
            "datetime_end": "2026-10-01T13:00:00Z",
            "max_pilots": 20,
            "car_class": "GT3",
            "track": "Test track",
            "briefing_start_time": "11:30",
            "briefing_end_time": "11:45",
            "required_pit_stops": 2,
        })

        self.assertEqual(update.model_dump(exclude_unset=True), {
            "briefing_start_time": time(19, 0),
            "briefing_end_time": time(19, 15),
            "required_pit_stops": 2,
        })
        self.assertEqual(created.briefing_start_time, time(11, 30))
        self.assertEqual(created.briefing_end_time, time(11, 45))
        self.assertEqual(created.required_pit_stops, 2)

    def test_required_pit_stops_are_bounded(self):
        for value in (-1, 21):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                RaceUpdate.model_validate({"required_pit_stops": value})
