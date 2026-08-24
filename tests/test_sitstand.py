from datetime import datetime
from zoneinfo import ZoneInfo

from eightbit_buddy.sitstand import _payload, in_working_hours

TZ = ZoneInfo("Australia/Melbourne")


def test_working_hours_weekday_boundaries() -> None:
    assert in_working_hours(datetime(2026, 8, 24, 9, 0, tzinfo=TZ))
    assert in_working_hours(datetime(2026, 8, 24, 17, 29, tzinfo=TZ))
    assert not in_working_hours(datetime(2026, 8, 24, 8, 59, tzinfo=TZ))
    assert not in_working_hours(datetime(2026, 8, 24, 17, 30, tzinfo=TZ))


def test_working_hours_excludes_weekend() -> None:
    assert not in_working_hours(datetime(2026, 8, 22, 10, 0, tzinfo=TZ))
    assert not in_working_hours(datetime(2026, 8, 23, 10, 0, tzinfo=TZ))


def test_notification_payloads() -> None:
    sitting = _payload(False)
    standing = _payload(True)
    assert sitting["text"] == "SIT DOWN - 30 MIN"
    assert sitting["color"] == "#00E676"
    assert standing["text"] == "STAND UP - 15 MIN"
    assert standing["color"] == "#FF9800"
