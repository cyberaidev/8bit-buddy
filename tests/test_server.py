from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request

from eightbit_buddy.config import AppConfig, ServerSettings
from eightbit_buddy.display import DisplayBackend
from eightbit_buddy.model import AgentEvent, AgentState
from eightbit_buddy.server import BeaconServer
from eightbit_buddy.store import AgentRecord


class FakeDisplay(DisplayBackend):
    def __init__(self) -> None:
        self.shown: list[AgentRecord] = []
        self.deleted: list[AgentRecord] = []

    def show(self, record: AgentRecord) -> None:
        self.shown.append(record)

    def delete(self, record: AgentRecord) -> None:
        self.deleted.append(record)


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.display = FakeDisplay()
        config = AppConfig(server=ServerSettings(port=0, token="test-token"))
        self.server = BeaconServer(config, self.display)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path: str, *, data: object | None = None, token: str = "test-token"):
        headers = {"X-8bit-Buddy-Token": token}
        body = None
        if data is not None:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        return urllib.request.urlopen(
            urllib.request.Request(self.base + path, data=body, headers=headers), timeout=2
        )

    def test_event_is_accepted_and_listed(self) -> None:
        event = AgentEvent(
            provider="codex",
            agent_key="codex:s1:main",
            name="Codex · project",
            state=AgentState.RUNNING,
            session_id="s1",
        )
        with self.request("/v1/events", data=event.to_dict()) as response:
            self.assertEqual(response.status, 202)
        self.assertEqual(len(self.display.shown), 1)
        with self.request("/v1/agents") as response:
            payload = json.load(response)
        self.assertEqual(payload["agents"][0]["state"], "running")

    def test_wrong_token_is_rejected(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as context:
            self.request("/health", token="wrong")
        self.assertEqual(context.exception.code, 401)


if __name__ == "__main__":
    unittest.main()
