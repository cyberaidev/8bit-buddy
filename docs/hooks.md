# Hook integration details

8bit Buddy uses documented lifecycle hooks and does not watch processes, scrape screens, or parse
unstable transcript formats.

## Normalised lifecycle

| Normalised state | Codex | Claude Code | Cursor |
| --- | --- | --- | --- |
| Working | `UserPromptSubmit`, `SubagentStart` | `UserPromptSubmit`, `SubagentStart` | `beforeSubmitPrompt`, `subagentStart` |
| Needs you | `PermissionRequest`, explicit final request | `PermissionRequest`, selected `Notification` types, explicit final request | Explicit final request |
| Done | `Stop`, `SubagentStop` | `Stop`, `SubagentStop`, completion notifications | `stop: completed`, `subagentStop: completed` |
| Error | — | `StopFailure` | `stop/subagentStop: error` |

The final-message classifier is deliberately conservative. Permission events always win. If a stop
event includes or follows a final message such as “Please choose the production account,” it becomes
`attention`; a normal completion remains `complete`.

## Codex

Configuration is added to `~/.codex/hooks.json`. Codex command hooks receive JSON over standard
input. The integration uses stable hook fields such as `session_id`, `cwd`, `hook_event_name`,
`agent_id`, and `agent_type` when present.

After installation, open `/hooks` in Codex and trust the new commands. Codex hashes hook definitions
and skips new or changed non-managed hooks until they have been reviewed.

Official reference: [Codex hooks](https://learn.chatgpt.com/docs/hooks)

## Claude Code

Configuration is merged into `~/.claude/settings.json`. In addition to start/stop events, Claude
Code exposes notification types that map cleanly to a physical beacon:

- `permission_prompt`, `elicitation_dialog`, and `agent_needs_input` → red
- `idle_prompt` and `agent_completed` → green

Claude's `Stop` and `SubagentStop` payloads include `last_assistant_message`. If background tasks are
still running, the apparent stop remains blue rather than becoming green.

Official reference: [Claude Code hooks](https://code.claude.com/docs/en/hooks)

## Cursor

Configuration is merged into `~/.cursor/hooks.json`. Cursor provides a common schema containing
`conversation_id`, `generation_id`, `hook_event_name`, `workspace_roots`, and `transcript_path`.
8bit Buddy does not read the transcript.

The `afterAgentResponse` event caches the final text in memory. The following `stop` event provides
the authoritative `completed`, `aborted`, or `error` status. Cursor subagent stop payloads currently
omit the start event's `subagent_id`, so 8bit Buddy correlates the pair with a hash of the documented
subagent type and task.

Official reference: [Cursor hooks](https://cursor.com/docs/hooks)

## Hook safety

Every hook command:

- has a five-second vendor timeout;
- normally returns in under a second;
- emits no stdout that could alter agent behaviour;
- catches adapter and network errors;
- exits zero if the local service or display is unavailable.

The display is observability, not a control-plane dependency. It must never prevent an agent from
working.

## Local versus cloud agents

This release is macOS-local-first. Global user hooks run where the local Codex, Claude Code, or
Cursor client runs and can reach `127.0.0.1:7391`. A hook executing inside a remote cloud agent VM
cannot reach the Mac's loopback service. Remote relay support is intentionally out of scope until it
can be added with explicit authentication and transport security.
