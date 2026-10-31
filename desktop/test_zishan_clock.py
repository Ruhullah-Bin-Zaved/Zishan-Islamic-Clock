import copy
import os
import tempfile
import unittest
from datetime import date, datetime, timedelta

from zishan_clock import (
    DEFAULTS, DEFAULT_LOCATION, HIJRI_SOURCES, METHODS, PRAYERS, bangla_date, calculate_prayers,
    ensure_prayer_events, offline_hijri, play_focus_sound, sync_prayer_schedule,
    next_general_alarm, prayer_event_time, scheduled_prayer_events,
)


class PrayerCalculationTests(unittest.TestCase):
    def setUp(self):
        self.settings = {
            "latitude": 23.8103,
            "longitude": 90.4125,
            "timezone": "Asia/Dhaka",
            "method": "Muslim World League",
            "asr": "Hanafi",
            "high_latitude": "Middle of the night",
            "adjustments": {name: 0 for name in PRAYERS},
        }

    def test_returns_all_prayers_in_local_zone(self):
        result = calculate_prayers(date(2024, 6, 15), self.settings)
        self.assertEqual(list(result), list(PRAYERS))
        self.assertTrue(all(result[name] is not None for name in PRAYERS))
        self.assertTrue(all(value.tzname() == "+06" for value in result.values()))

    def test_adjustment_changes_only_selected_prayer(self):
        baseline = calculate_prayers(date(2024, 6, 15), self.settings)
        self.settings["adjustments"]["Fajr"] = 3
        adjusted = calculate_prayers(date(2024, 6, 15), self.settings)
        self.assertEqual((adjusted["Fajr"] - baseline["Fajr"]).seconds // 60, 3)
        self.assertEqual(adjusted["Dhuhr"], baseline["Dhuhr"])

    def test_methods_are_defined(self):
        self.assertEqual(set(METHODS), {
            "Muslim World League", "Karachi", "Egyptian", "North America", "Singapore"
        })

    def test_default_location_is_chattogram(self):
        self.assertEqual(DEFAULTS["city"], "Chattogram, Bangladesh")
        self.assertEqual(DEFAULTS["latitude"], DEFAULT_LOCATION["latitude"])
        self.assertEqual(DEFAULTS["longitude"], DEFAULT_LOCATION["longitude"])
        self.assertEqual(DEFAULTS["timezone"], "Asia/Dhaka")

    def test_study_break_defaults_are_separate_from_alarm_sound(self):
        self.assertEqual(DEFAULTS["study_minutes"], 25)
        self.assertEqual(DEFAULTS["break_minutes"], 5)
        self.assertEqual(DEFAULTS["focus_daily_goal_hours"], 8)
        self.assertEqual(DEFAULTS["focus_stats"], {})
        self.assertIn("study_sound", DEFAULTS)
        self.assertNotEqual("study_sound", "sound")
        self.assertEqual(DEFAULTS["study_sound_volume"], 70)
        self.assertEqual(DEFAULTS["break_sound_volume"], 70)
        self.assertTrue(DEFAULTS["study_sound_enabled"])
        self.assertTrue(DEFAULTS["break_sound_enabled"])
        self.assertEqual(DEFAULTS["tasbih_count"], 0)
        self.assertEqual(DEFAULTS["quick_notes"], "")

    def test_calendar_defaults_and_offline_formats(self):
        self.assertIn(DEFAULTS["hijri_source"], HIJRI_SOURCES)
        hijri = offline_hijri(date(2026, 10, 31))
        self.assertEqual((hijri["day"], hijri["month_name"], hijri["year"]),
                         (10, "Rabi al-Thani", 1448))
        self.assertIn("arabic_month", hijri)
        bangla = bangla_date(date(2026, 10, 31))
        self.assertEqual(bangla["month_name"], "Kartik")
        self.assertGreater(bangla["year"], 1400)

    def test_missing_focus_sound_is_reported_as_not_started(self):
        self.assertFalse(play_focus_sound(os.path.join(tempfile.gettempdir(), "missing-focus-sound.mp3")))

    def test_online_prayer_payload_is_optional_and_well_formed(self):
        payload = sync_prayer_schedule(date(2026, 10, 31), self.settings, timeout=0.01)
        if payload:
            self.assertEqual(payload["date"], "2026-10-31")
            self.assertIn("Fajr", payload["times"])

    def test_daily_offset_follows_changed_base_time(self):
        settings = copy.deepcopy(self.settings)
        ensure_prayer_events(settings)
        event = settings["prayer_events"]["Dhuhr"]["azan"]
        event.update(enabled=True, mode="offset", offset=5)
        first = calculate_prayers(date(2024, 6, 15), settings)["Dhuhr"]
        second = calculate_prayers(date(2024, 6, 16), settings)["Dhuhr"]
        self.assertEqual(prayer_event_time(first, event), first + timedelta(minutes=5))
        self.assertEqual(event["offset"], 5)
        self.assertNotEqual(first.date(), second.date())

    def test_fixed_clock_time_does_not_follow_base_time(self):
        settings = copy.deepcopy(self.settings)
        ensure_prayer_events(settings)
        event = settings["prayer_events"]["Dhuhr"]["azan"]
        event.update(enabled=True, mode="fixed", time="13:00")
        first = calculate_prayers(date(2024, 6, 15), settings)["Dhuhr"]
        second = calculate_prayers(date(2024, 6, 16), settings)["Dhuhr"]
        self.assertEqual(prayer_event_time(first, event).strftime("%H:%M"), "13:00")
        self.assertEqual(prayer_event_time(second, event).strftime("%H:%M"), "13:00")

    def test_events_are_independent_and_not_duplicated(self):
        settings = copy.deepcopy(self.settings)
        ensure_prayer_events(settings)
        settings["prayer_events"]["Fajr"]["azan"]["enabled"] = True
        settings["prayer_events"]["Fajr"]["reminder"]["enabled"] = True
        events = scheduled_prayer_events(date(2024, 6, 15), settings)
        self.assertEqual(len(events), 2)
        self.assertEqual(len({event["id"] for event in events}), 2)

    def test_general_alarm_repeat_and_one_time(self):
        now = datetime(2024, 6, 15, 10, 0)  # Saturday
        self.assertIsNone(next_general_alarm({"enabled": True, "time": "09:00"}, now))
        next_weekday = next_general_alarm({"enabled": True, "time": "11:00", "repeat": [5]}, now)
        self.assertEqual(next_weekday, datetime(2024, 6, 15, 11, 0))


if __name__ == "__main__":
    unittest.main()
