from __future__ import annotations

import argparse
import sys
import time
import urllib.error
from datetime import datetime, time as clock_time
from pathlib import Path
from zoneinfo import ZoneInfo

from .awtrix import AwtrixClient
from .config import AppConfig, default_config_path, load_config
from .display import _safe_app_name

WEEKDAYS = frozenset(range(5))
DEFAULT_TIMEZONE = "Australia/Melbourne"
SIT_SECONDS = 30 * 60
STAND_SECONDS = 15 * 60
UPDATE_SECONDS = 60


def in_working_hours(now: datetime) -> bool:
    local_time = now.timetz().replace(tzinfo=None)
    return now.weekday() in WEEKDAYS and clock_time(9, 0) <= local_time < clock_time(17, 30)


def _notification_payload(standing: bool, icon: str = "") -> dict[str, object]:
    if standing:
        payload: dict[str, object] = {
            "text": "STAND UP - 15 MIN",
            "color": "#FF9800",
            "duration": 8,
            "rtttl": "stand:d=8,o=6,b=120:c,e,g",
            "stack": False,
            "wakeup": True,
        }
    else:
        payload = {
            "text": "SIT DOWN - 30 MIN",
            "color": "#00E676",
            "duration": 8,
            "rtttl": "sit:d=8,o=6,b=120:g,e,c",
            "stack": False,
            "wakeup": True,
        }
    if icon:
        payload["icon"] = icon
    return payload


def _payload(standing: bool) -> dict[str, object]:
    """Backward-compatible notification payload helper used by older integrations."""
    return _notification_payload(standing)


def _app_payload(
    standing: bool,
    remaining_seconds: int,
    *,
    icon: str = "",
) -> dict[str, object]:
    total = STAND_SECONDS if standing else SIT_SECONDS
    remaining = max(0, min(total, remaining_seconds))
    minutes = max(0, (remaining + 59) // 60)
    progress = round(remaining / total * 100) if total else 0
    color = "#FF9800" if standing else "#00E676"
    payload: dict[str, object] = {
        "text": f"{'STAND' if standing else 'SIT'} {minutes}m",
        "textCase": 2,
        "center": True,
        "color": color,
        "background": "#000000",
        "progress": progress,
        "progressC": color,
        "progressBC": "#202020",
        "lifetime": UPDATE_SECONDS * 3,
        "lifetimeMode": 0,
    }
    if icon:
        payload["icon"] = icon
        payload["pushIcon"] = 2
    return payload


def _phase_icon(config: AppConfig, standing: bool) -> str:
    return config.icons.standing if standing else config.icons.sitting


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

    client = AwtrixClient(config.display.host, timeout=config.display.timeout_seconds)
    app_name = f"{_safe_app_name(config.display.app_prefix)}_sitstand"
    tz = ZoneInfo(timezone)
    now_fn = now_fn or (lambda: datetime.now(tz))
    standing = False

    while True:
        phase_start = now_fn()
        if not in_working_hours(phase_start):
            return 0

        icon = _phase_icon(config, standing)
        try:
            client.notify(_notification_payload(standing, icon))
        except (OSError, urllib.error.URLError) as exc:
            print(f"TC001 notification failed: {exc}", file=sys.stderr)

        phase_seconds = STAND_SECONDS if standing else SIT_SECONDS
        elapsed = 0
        while elapsed < phase_seconds:
            now = now_fn()
            if not in_working_hours(now):
                try:
                    client.delete_custom_app(app_name)
                except (OSError, urllib.error.URLError):
                    pass
                return 0

            remaining = phase_seconds - elapsed
            try:
                client.custom_app(
                    app_name,
                    _app_payload(standing, remaining, icon=icon),
                )
            except (OSError, urllib.error.URLError) as exc:
                print(f"TC001 dashboard update failed: {exc}", file=sys.stderr)

            until_close = (
                now.replace(hour=17, minute=30, second=0, microsecond=0) - now
            ).total_seconds()
            if until_close <= 0:
                return 0
            step = min(UPDATE_SECONDS, phase_seconds - elapsed, until_close)
            sleep_fn(step)
            elapsed += step

        standing = not standing


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
