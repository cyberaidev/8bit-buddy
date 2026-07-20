from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

PROVIDER_TITLES = {
    "codex": "Codex",
    "claude": "Claude",
    "cursor": "Cursor",
    "demo": "Demo",
}


def _clean(value: object, fallback: str) -> str:
    text = " ".join(str(value or "").split()).strip(" /·")
    return text[:64] or fallback


def workspace_name(payload: dict[str, Any]) -> str:
    roots = payload.get("workspace_roots")
    candidate = roots[0] if isinstance(roots, list) and roots else payload.get("cwd")
    if candidate:
        return _clean(Path(str(candidate)).name, "workspace")
    return "workspace"


def session_id(payload: dict[str, Any]) -> str:
    for key in ("session_id", "conversation_id", "thread_id", "generation_id"):
        value = payload.get(key)
        if value:
            return str(value)
    return f"cwd:{payload.get('cwd') or workspace_name(payload)}"


def main_identity(provider: str, payload: dict[str, Any]) -> tuple[str, str, str]:
    session = session_id(payload)
    title = PROVIDER_TITLES.get(provider, provider.title())
    name = f"{title} · {workspace_name(payload)}"
    return f"{provider}:{session}:main", name, session


def subagent_identity(provider: str, payload: dict[str, Any]) -> tuple[str, str, str]:
    session = session_id(payload)
    agent_type = _clean(payload.get("agent_type") or payload.get("subagent_type"), "subagent")

    # Cursor currently emits subagent_id at start but not at stop. A task hash keeps
    # both lifecycle events correlated without scraping its transcript.
    if provider == "cursor":
        task = str(payload.get("task") or payload.get("description") or agent_type)
        token = hashlib.sha256(f"{agent_type}\0{task}".encode()).hexdigest()[:12]
    else:
        token = str(payload.get("agent_id") or payload.get("subagent_id") or agent_type)

    title = PROVIDER_TITLES.get(provider, provider.title())
    name = f"{title} · {agent_type}"
    return f"{provider}:{session}:sub:{token}", name, session
