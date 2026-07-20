from __future__ import annotations

import unittest

from eightbit_buddy.adapters import adapt_hook
from eightbit_buddy.config import TTLSettings
from eightbit_buddy.model import AgentState
from eightbit_buddy.store import StateStore


class AdapterTests(unittest.TestCase):
    def test_codex_prompt_starts_main_agent(self) -> None:
        event = adapt_hook(
            "codex",
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": "session-1",
                "cwd": "/Users/stefano/code/payments",
            },
        )
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.state, AgentState.RUNNING)
        self.assertEqual(event.name, "Codex · payments")
        self.assertEqual(event.agent_key, "codex:session-1:main")

    def test_codex_permission_needs_attention(self) -> None:
        event = adapt_hook(
            "codex",
            {
                "hook_event_name": "PermissionRequest",
                "session_id": "session-1",
                "cwd": "/tmp/project",
                "tool_name": "Bash",
            },
        )
        assert event is not None
        self.assertEqual(event.state, AgentState.ATTENTION)
        self.assertEqual(event.detail, "Bash")

    def test_claude_final_question_becomes_attention(self) -> None:
        event = adapt_hook(
            "claude",
            {
                "hook_event_name": "Stop",
                "session_id": "session-2",
                "cwd": "/tmp/project",
                "last_assistant_message": "Please choose the production AWS account.",
                "background_tasks": [],
            },
        )
        assert event is not None
        record = StateStore(TTLSettings()).apply(event)
        assert record is not None
        self.assertEqual(record.state, AgentState.ATTENTION)

    def test_claude_normal_stop_is_complete(self) -> None:
        event = adapt_hook(
            "claude",
            {
                "hook_event_name": "Stop",
                "session_id": "session-2",
                "cwd": "/tmp/project",
                "last_assistant_message": "Implementation complete and all tests pass.",
                "background_tasks": [],
            },
        )
        assert event is not None
        record = StateStore(TTLSettings()).apply(event)
        assert record is not None
        self.assertEqual(record.state, AgentState.COMPLETE)

    def test_claude_background_task_remains_running(self) -> None:
        event = adapt_hook(
            "claude",
            {
                "hook_event_name": "Stop",
                "session_id": "session-2",
                "cwd": "/tmp/project",
                "background_tasks": [{"id": "task-1", "status": "running"}],
            },
        )
        assert event is not None
        self.assertEqual(event.state, AgentState.RUNNING)

    def test_cursor_caches_response_before_stop(self) -> None:
        store = StateStore(TTLSettings())
        common = {
            "conversation_id": "conversation-1",
            "generation_id": "generation-1",
            "workspace_roots": ["/tmp/project"],
        }
        message = adapt_hook(
            "cursor",
            {
                **common,
                "hook_event_name": "afterAgentResponse",
                "text": "Can you confirm the region?",
            },
        )
        assert message is not None
        self.assertIsNone(store.apply(message))

        stopped = adapt_hook("cursor", {**common, "hook_event_name": "stop", "status": "completed"})
        assert stopped is not None
        record = store.apply(stopped)
        assert record is not None
        self.assertEqual(record.state, AgentState.ATTENTION)

    def test_cursor_subagent_start_and_stop_correlate(self) -> None:
        common = {
            "conversation_id": "conversation-1",
            "generation_id": "generation-1",
            "workspace_roots": ["/tmp/project"],
            "subagent_type": "explore",
            "task": "Map the authentication flow",
        }
        started = adapt_hook("cursor", {**common, "hook_event_name": "subagentStart"})
        stopped = adapt_hook(
            "cursor", {**common, "hook_event_name": "subagentStop", "status": "completed"}
        )
        assert started is not None and stopped is not None
        self.assertEqual(started.agent_key, stopped.agent_key)

    def test_unrelated_event_is_ignored(self) -> None:
        self.assertIsNone(adapt_hook("cursor", {"hook_event_name": "afterFileEdit"}))


if __name__ == "__main__":
    unittest.main()
