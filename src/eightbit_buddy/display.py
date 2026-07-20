from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import urllib.parse
import urllib.request

from .config import AppConfig
from .model import AgentState
from .store import AgentRecord

STATE_LABELS = {
    AgentState.RUNNING: "WORKING",
    AgentState.ATTENTION: "NEEDS YOU",
    AgentState.COMPLETE: "DONE",
    AgentState.ERROR: "ERROR",
}


class DisplayBackend:
    def show(self, record: AgentRecord) -> None:
        raise NotImplementedError

    def delete(self, record: AgentRecord) -> None:
        raise NotImplementedError

    def check(self) -> bool:
        return True


class ConsoleDisplay(DisplayBackend):
    def __init__(self) -> None:
        self.log = logging.getLogger("eightbit_buddy.display")

    def show(self, record: AgentRecord) -> None:
        self.log.info("%s — %s", record.name, STATE_LABELS[record.state])

    def delete(self, record: AgentRecord) -> None:
        self.log.info("expired — %s", record.name)


class AwtrixDisplay(DisplayBackend):
    def __init__(self, config: AppConfig) -> None:
        host = config.display.host.strip().rstrip("/")
        if not host:
            raise ValueError("display.host is required for the AWTRIX driver")
        self.base_url = host if "://" in host else f"http://{host}"
        self.timeout = config.display.timeout_seconds
        self.prefix = _safe_app_name(config.display.app_prefix)
        self.scroll_speed = config.display.scroll_speed
        self.colors = config.colors
        self._lock = threading.Lock()

    def app_name(self, record: AgentRecord) -> str:
        digest = hashlib.sha256(record.agent_key.encode()).hexdigest()[:10]
        return f"{self.prefix}_{digest}"

    def payload(self, record: AgentRecord) -> dict[str, object]:
        color = getattr(self.colors, record.state.value)
        lifetime = max(1, int(record.expires_at - record.updated_at))
        payload: dict[str, object] = {
            "text": f"{record.name}  {STATE_LABELS[record.state]}",
            "textCase": 2,
            "center": True,
            "color": color,
            "background": self.colors.background,
            "scrollSpeed": self.scroll_speed,
            "lifetime": lifetime,
            "lifetimeMode": 0,
        }
        if record.state in {AgentState.ATTENTION, AgentState.ERROR}:
            payload["blinkText"] = 500
        return payload

    def _post(self, path: str, data: bytes) -> None:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self._lock, urllib.request.urlopen(request, timeout=self.timeout):
            pass

    def show(self, record: AgentRecord) -> None:
        name = urllib.parse.quote(self.app_name(record), safe="")
        self._post(f"/api/custom?name={name}", json.dumps(self.payload(record)).encode())

    def delete(self, record: AgentRecord) -> None:
        name = urllib.parse.quote(self.app_name(record), safe="")
        self._post(f"/api/custom?name={name}", b"")

    def check(self) -> bool:
        request = urllib.request.Request(f"{self.base_url}/api/stats", method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status == 200
        except OSError:
            return False


def _safe_app_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", value)[:20]
    return cleaned or "8bitbuddy"


def build_display(config: AppConfig) -> DisplayBackend:
    if config.display.driver == "console":
        return ConsoleDisplay()
    if config.display.driver == "awtrix":
        return AwtrixDisplay(config)
    raise ValueError(f"unsupported display driver: {config.display.driver}")
