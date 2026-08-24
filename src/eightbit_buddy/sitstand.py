from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, time as clock_time
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import default_config_path, load_config

WEEKDAYS = frozenset(range(5))
DEFAULT_TIMEZONE = "Australia/Melbourne"


def in_working_hours(now: datetime) -> bool:
    local_time = now.timetz().replace(tzinfo=None)
    return now.weekday() in WEEKDAYS and clock_time(9, 0) <= local_time < clock_time(17, 30)


def _notify(host: str, payload: dict[str, object], timeout: float) -> None:
    base = host.strip().rstrip("/")
    if not base:
        raise ValueError("display.host is required")
    if "://" not in base:
        base = f"http://{base}"
    request = urllib.request.Request(
        f"{base}/api/notify",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout):
        pass


def _payload(standing: bool) -> dict[str, object]:
    if standing:
        return {
            "text": "STAND UP - 15 MIN",
            "color": "#FF9800",
            "duration": 8,
            "rtttl": "stand:d=8,o=6,b=120:c,e,g",
            "stack": False,
            "wakeup": True,
        }
    return {
        "text": "SIT DOWN - 30 MIN",
        "color": "#00E676",
        "duration": 8,
        "rtttl": "sit:d=8,o=6,b=120:g,e,c",
        "stack": False,
        "wakeup": True,
    }


def run(
    config_path: Path,
    *,
    timezone: str = DEFAULT_TIMEZONE,
    sleep_fn=time.sleep,
    now_fn=None,
) -> int:
    config = load_config(config_path)
    if config.display.driver != "awtrix":
        raise ValueError('sit/stand reminders require display.driver = "awtrix"')

    tz = ZoneInfo(timezone)
    now_fn = now_fn or (lambda: datetime.now(tz))
    standing = False

    while True:
        now = now_fn()
        if not in_working_hours(now):
            return 0

        try:
            _notify(
                config.display.host,
                _payload(standing),
                config.display.timeout_seconds,
            )
        except (OSError, urllib.error.URLError) as exc:
            print(f"TC001 notification failed: {exc}", file=sys.stderr)

        seconds = 900 if standing else 1800
        standing = not standing

        remaining = (
            now.replace(hour=17, minute=30, second=0, microsecond=0) - now
        ).total_seconds()
        if remaining <= 0:
            return 0
        sleep_fn(min(seconds, remaining))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Weekday sit/stand reminders for an AWTRIX TC001.")
    parser.add_argument("--config", type=Path, default=default_config_path())
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args.config.expanduser(), timezone=args.timezone)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
