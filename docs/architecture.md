# Architecture

## Components

| Component | Responsibility |
| --- | --- |
| Hook adapter | Convert one vendor event into a small provider-neutral event |
| Loopback client | POST the event with a short timeout and fail open |
| Local service | Authenticate, classify, and retain current agent state in memory |
| State store | Correlate messages/stops, manage concurrent agents, and expire pages |
| AWTRIX driver | Create, update, and delete one custom app per agent |
| macOS LaunchAgent | Keep the service running after login |

## Event flow

1. A user submits a prompt or an agent lifecycle event fires.
2. The vendor starts `8bit-buddy hook <provider>` and sends JSON on standard input.
3. The adapter extracts only identity and lifecycle fields.
4. The hook POSTs a normalised event to `127.0.0.1:7391/v1/events`.
5. The service stores current state and generates a stable AWTRIX app name from the agent key.
6. The AWTRIX device updates or rotates the custom page.
7. Completed pages expire after two minutes by default; attention pages remain for one hour or until
   the next prompt changes their state.

## State and privacy

State is intentionally ephemeral. The daemon keeps an `AgentRecord` and, where needed, one recent
assistant message per active agent. Nothing is written to a database or log. The hook payload's
prompt and transcript paths are not forwarded as display content.

## Extension points

The `DisplayBackend` interface keeps hardware separate from lifecycle logic. A future backend can
support another local display without changing any vendor adapter. New providers should implement a
small adapter returning the existing `AgentEvent` model and include fixture-based unit tests.
