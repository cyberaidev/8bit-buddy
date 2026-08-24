from __future__ import annotations

import hashlib
import logging
import re

from .awtrix import AwtrixClient
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
        self.client = AwtrixClient(
            config.display.host,
            timeout=config.display.timeout_seconds,
        )
        self.prefix = _safe_app_name(config.display.app_prefix)
        self.scroll_speed = config.display.scroll_speed
        self.colors = config.colors
        self.icons = config.icons

    def app_name(self, record: AgentRecord) -> str:
        digest = hashlib.sha256(record.agent_key.encode()).hexdigest()[:10]
        return f"{self.prefix}_{digest}"

    def payload(self, record: AgentRecord) -> dict[str, object]:
        color = getattr(self.colors, record.state.value)
        icon = getattr(self.icons, record.state.value)
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
        if icon:
            payload["icon"] = icon
            payload["pushIcon"] = 2
        if record.state in {AgentState.ATTENTION, AgentState.ERROR}:
            payload["blinkText"] = 500
        if record.state == AgentState.COMPLETE:
            payload["progress"] = 100
            payload["progressC"] = color
        return payload

    def show(self, record: AgentRecord) -> None:
        self.client.custom_app(self.app_name(record), self.payload(record))

    def delete(self, record: AgentRecord) -> None:
        self.client.delete_custom_app(self.app_name(record))

    def check(self) -> bool:
        return self.client.check()


def _safe_app_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", value)[:20]
    return cleaned or "8bitbuddy"


def build_display(config: AppConfig) -> DisplayBackend:
    if config.display.driver == "console":
        return ConsoleDisplay()
    if config.display.driver == "awtrix":
        return AwtrixDisplay(config)
    raise ValueError(f"unsupported display driver: {config.display.driver}")
