from __future__ import annotations

import unittest

from eightbit_buddy.config import AppConfig, DisplaySettings
from eightbit_buddy.display import AwtrixDisplay
from eightbit_buddy.model import AgentState
from eightbit_buddy.store import AgentRecord


class DisplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.display = AwtrixDisplay(
            AppConfig(display=DisplaySettings(driver="awtrix", host="display.local"))
        )

    def record(self, state: AgentState) -> AgentRecord:
        return AgentRecord(
            agent_key="codex:123:main",
            provider="codex",
            name="Codex · checkout",
            state=state,
            detail="",
            session_id="123",
            updated_at=100,
            expires_at=220,
        )

    def test_payload_uses_requested_status_colours(self) -> None:
        attention = self.display.payload(self.record(AgentState.ATTENTION))
        complete = self.display.payload(self.record(AgentState.COMPLETE))
        self.assertEqual(attention["color"], "#FF1744")
        self.assertEqual(attention["blinkText"], 500)
        self.assertEqual(complete["color"], "#00E676")
        self.assertNotIn("blinkText", complete)

    def test_app_name_is_stable_and_awtrix_safe(self) -> None:
        first = self.display.app_name(self.record(AgentState.RUNNING))
        second = self.display.app_name(self.record(AgentState.COMPLETE))
        self.assertEqual(first, second)
        self.assertRegex(first, r"^[a-zA-Z0-9_]+$")


if __name__ == "__main__":
    unittest.main()
