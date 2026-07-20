from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

from .attention import needs_user_attention
from .config import TTLSettings
from .model import AgentEvent, AgentState


@dataclass(slots=True)
class AgentRecord:
    agent_key: str
    provider: str
    name: str
    state: AgentState
    detail: str
    session_id: str
    updated_at: float
    expires_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_key": self.agent_key,
            "provider": self.provider,
            "name": self.name,
            "state": self.state.value,
            "detail": self.detail,
            "session_id": self.session_id,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
        }


class StateStore:
    def __init__(self, ttl: TTLSettings) -> None:
        self._ttl = ttl
        self._records: dict[str, AgentRecord] = {}
        self._last_messages: dict[str, str] = {}
        self._lock = threading.RLock()

    def _ttl_for(self, state: AgentState) -> int:
        return int(getattr(self._ttl, state.value))

    def apply(self, event: AgentEvent) -> AgentRecord | None:
        with self._lock:
            if event.state is None:
                if event.detail:
                    self._last_messages[event.agent_key] = event.detail
                return None

            state = event.state
            detail = event.detail or self._last_messages.get(event.agent_key, "")
            if (
                state == AgentState.COMPLETE
                and event.classify_attention
                and needs_user_attention(detail)
            ):
                state = AgentState.ATTENTION

            if state == AgentState.RUNNING:
                self._last_messages.pop(event.agent_key, None)
            elif detail:
                self._last_messages[event.agent_key] = detail

            now = event.timestamp or time.time()
            record = AgentRecord(
                agent_key=event.agent_key,
                provider=event.provider,
                name=event.name,
                state=state,
                detail=detail,
                session_id=event.session_id,
                updated_at=now,
                expires_at=now + self._ttl_for(state),
            )
            self._records[event.agent_key] = record
            return record

    def list(self) -> list[AgentRecord]:
        with self._lock:
            return sorted(self._records.values(), key=lambda item: item.updated_at, reverse=True)

    def pop_expired(self, now: float | None = None) -> list[AgentRecord]:
        now = now or time.time()
        expired: list[AgentRecord] = []
        with self._lock:
            for key, record in list(self._records.items()):
                if record.expires_at <= now:
                    expired.append(self._records.pop(key))
                    self._last_messages.pop(key, None)
        return expired
