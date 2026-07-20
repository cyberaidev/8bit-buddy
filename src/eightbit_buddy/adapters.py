from __future__ import annotations

from typing import Any

from .model import AgentEvent, AgentState
from .naming import main_identity, subagent_identity

SUPPORTED_PROVIDERS = ("codex", "claude", "cursor")


def _event(
    provider: str,
    payload: dict[str, Any],
    state: AgentState | None,
    *,
    subagent: bool = False,
    detail: str = "",
    classify_attention: bool = False,
    name_override: str | None = None,
) -> AgentEvent:
    identity = subagent_identity if subagent else main_identity
    key, name, session = identity(provider, payload)
    return AgentEvent(
        provider=provider,
        agent_key=key,
        name=name_override or name,
        state=state,
        detail=detail,
        session_id=session,
        classify_attention=classify_attention,
    )


def _last_message(payload: dict[str, Any]) -> str:
    return str(
        payload.get("last_assistant_message")
        or payload.get("text")
        or payload.get("message")
        or payload.get("summary")
        or ""
    )


def _adapt_codex(payload: dict[str, Any], name_override: str | None) -> AgentEvent | None:
    event = str(payload.get("hook_event_name") or "").lower()
    if event in {"userpromptsubmit", "sessionstart"}:
        return _event("codex", payload, AgentState.RUNNING, name_override=name_override)
    if event == "permissionrequest":
        tool = str(payload.get("tool_name") or "approval")
        return _event(
            "codex", payload, AgentState.ATTENTION, detail=tool, name_override=name_override
        )
    if event == "subagentstart":
        return _event(
            "codex", payload, AgentState.RUNNING, subagent=True, name_override=name_override
        )
    if event == "subagentstop":
        return _event(
            "codex",
            payload,
            AgentState.COMPLETE,
            subagent=True,
            detail=_last_message(payload),
            classify_attention=True,
            name_override=name_override,
        )
    if event == "stop":
        if payload.get("background_tasks"):
            return _event("codex", payload, AgentState.RUNNING, name_override=name_override)
        return _event(
            "codex",
            payload,
            AgentState.COMPLETE,
            detail=_last_message(payload),
            classify_attention=True,
            name_override=name_override,
        )
    return None


def _adapt_claude(payload: dict[str, Any], name_override: str | None) -> AgentEvent | None:
    event = str(payload.get("hook_event_name") or "").lower()
    if event in {"userpromptsubmit", "sessionstart"}:
        return _event("claude", payload, AgentState.RUNNING, name_override=name_override)
    if event == "permissionrequest":
        return _event(
            "claude",
            payload,
            AgentState.ATTENTION,
            detail=str(payload.get("tool_name") or "approval"),
            name_override=name_override,
        )
    if event == "notification":
        notification = str(payload.get("notification_type") or "")
        if notification in {"permission_prompt", "elicitation_dialog", "agent_needs_input"}:
            return _event(
                "claude",
                payload,
                AgentState.ATTENTION,
                detail=_last_message(payload),
                name_override=name_override,
            )
        if notification in {"idle_prompt", "agent_completed"}:
            return _event("claude", payload, AgentState.COMPLETE, name_override=name_override)
        return None
    if event == "subagentstart":
        return _event(
            "claude", payload, AgentState.RUNNING, subagent=True, name_override=name_override
        )
    if event == "subagentstop":
        return _event(
            "claude",
            payload,
            AgentState.COMPLETE,
            subagent=True,
            detail=_last_message(payload),
            classify_attention=True,
            name_override=name_override,
        )
    if event == "stopfailure":
        return _event(
            "claude", payload, AgentState.ERROR, detail="stop failure", name_override=name_override
        )
    if event == "stop":
        if payload.get("background_tasks"):
            return _event("claude", payload, AgentState.RUNNING, name_override=name_override)
        return _event(
            "claude",
            payload,
            AgentState.COMPLETE,
            detail=_last_message(payload),
            classify_attention=True,
            name_override=name_override,
        )
    return None


def _adapt_cursor(payload: dict[str, Any], name_override: str | None) -> AgentEvent | None:
    event = str(payload.get("hook_event_name") or "").lower()
    if event in {"beforesubmitprompt", "sessionstart"}:
        return _event("cursor", payload, AgentState.RUNNING, name_override=name_override)
    if event == "subagentstart":
        return _event(
            "cursor", payload, AgentState.RUNNING, subagent=True, name_override=name_override
        )
    if event == "subagentstop":
        status = str(payload.get("status") or "completed")
        state = AgentState.COMPLETE if status == "completed" else AgentState.ERROR
        return _event(
            "cursor",
            payload,
            state,
            subagent=True,
            detail=_last_message(payload),
            classify_attention=status == "completed",
            name_override=name_override,
        )
    if event == "afteragentresponse":
        # Cursor's stop payload has status but no response text. Cache the preceding
        # message in the daemon so a final question can become red rather than green.
        return _event(
            "cursor", payload, None, detail=_last_message(payload), name_override=name_override
        )
    if event == "stop":
        status = str(payload.get("status") or "completed")
        state = AgentState.COMPLETE if status == "completed" else AgentState.ERROR
        return _event(
            "cursor",
            payload,
            state,
            classify_attention=status == "completed",
            name_override=name_override,
        )
    return None


def adapt_hook(
    provider: str, payload: dict[str, Any], *, name_override: str | None = None
) -> AgentEvent | None:
    provider = provider.lower()
    adapters = {
        "codex": _adapt_codex,
        "claude": _adapt_claude,
        "cursor": _adapt_cursor,
    }
    try:
        adapter = adapters[provider]
    except KeyError as exc:
        raise ValueError(f"unsupported provider: {provider}") from exc
    return adapter(payload, name_override)
