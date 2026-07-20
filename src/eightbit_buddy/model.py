from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class AgentState(StrEnum):
    RUNNING = "running"
    ATTENTION = "attention"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class AgentEvent:
    provider: str
    agent_key: str
    name: str
    state: AgentState | None
    detail: str = ""
    session_id: str = ""
    classify_attention: bool = False
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if not self.timestamp:
            object.__setattr__(self, "timestamp", time.time())

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "agent_key": self.agent_key,
            "name": self.name,
            "state": self.state.value if self.state else None,
            "detail": self.detail,
            "session_id": self.session_id,
            "classify_attention": self.classify_attention,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> AgentEvent:
        state_value = value.get("state")
        return cls(
            provider=str(value["provider"]),
            agent_key=str(value["agent_key"]),
            name=str(value["name"]),
            state=AgentState(state_value) if state_value else None,
            detail=str(value.get("detail") or ""),
            session_id=str(value.get("session_id") or ""),
            classify_attention=bool(value.get("classify_attention", False)),
            timestamp=float(value.get("timestamp") or 0),
        )
