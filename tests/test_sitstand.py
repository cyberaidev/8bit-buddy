import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from eightbit_buddy.sitstand import _app_payload, _payload, in_working_hours

TZ = ZoneInfo("Australia/Melbourne")


class SitStandTests(unittest.TestCase):
    def test_working_hours_weekday_boundaries(self) -> None:
        self.assertTrue(in_working_hours(datetime(2026, 8, 24, 9, 0, tzinfo=TZ)))
        self.assertTrue(in_working_hours(datetime(2026, 8, 24, 17, 29, tzinfo=TZ)))
        self.assertFalse(in_working_hours(datetime(2026, 8, 24, 8, 59, tzinfo=TZ)))
        self.assertFalse(in_working_hours(datetime(2026, 8, 24, 17, 30, tzinfo=TZ)))

    def test_working_hours_excludes_weekend(self) -> None:
        self.assertFalse(in_working_hours(datetime(2026, 8, 22, 10, 0, tzinfo=TZ)))
        self.assertFalse(in_working_hours(datetime(2026, 8, 23, 10, 0, tzinfo=TZ)))

    def test_notification_payloads(self) -> None:
        sitting = _payload(False)
        standing = _payload(True)
        self.assertEqual(sitting["text"], "SIT DOWN - 30 MIN")
        self.assertEqual(sitting["color"], "#00E676")
        self.assertEqual(standing["text"], "STAND UP - 15 MIN")
        self.assertEqual(standing["color"], "#FF9800")

    def test_dashboard_payload_has_countdown_progress_and_icon(self) -> None:
        sitting = _app_payload(False, 15 * 60, icon="chair")
        standing = _app_payload(True, 5 * 60, icon="stand")
        self.assertEqual(sitting["text"], "SIT 15m")
        self.assertEqual(sitting["progress"], 50)
        self.assertEqual(sitting["icon"], "chair")
        self.assertEqual(standing["text"], "STAND 5m")
        self.assertEqual(standing["progress"], 33)
        self.assertEqual(standing["icon"], "stand")


if __name__ == "__main__":
    unittest.main()
