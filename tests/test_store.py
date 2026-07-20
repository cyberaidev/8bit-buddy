from __future__ import annotations

import unittest

from eightbit_buddy.config import TTLSettings
from eightbit_buddy.model import AgentEvent, AgentState
from eightbit_buddy.store import StateStore


class StoreTests(unittest.TestCase):
    def test_expired_records_are_removed(self) -> None:
        store = StateStore(TTLSettings(complete=2))
        event = AgentEvent(
            "codex", "codex:s:main", "Codex · project", AgentState.COMPLETE, timestamp=100
        )
        store.apply(event)
        self.assertEqual(store.pop_expired(101), [])
        self.assertEqual(len(store.pop_expired(103)), 1)
        self.assertEqual(store.list(), [])


if __name__ == "__main__":
    unittest.main()
