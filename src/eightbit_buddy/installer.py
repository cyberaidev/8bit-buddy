from __future__ import annotations

import json
import os
import plistlib
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SERVICE_LABEL = "dev.cyberai.8bit-buddy"

HOOK_EVENTS = {
    "codex": (
        "UserPromptSubmit",
        "PermissionRequest",
        "SubagentStart",
        "SubagentStop",
        "Stop",
    ),
    "claude": (
        "UserPromptSubmit",
        "PermissionRequest",
        "Notification",
        "SubagentStart",
        "SubagentStop",
        "Stop",
        "StopFailure",
    ),
    "cursor": (
        "beforeSubmitPrompt",
        "subagentStart",
        "subagentStop",
        "afterAgentResponse",
        "stop",
    ),
}


def hook_path(provider: str, home: Path | None = None) -> Path:
    home = home or Path.home()
    paths = {
        "codex": home / ".codex" / "hooks.json",
        "claude": home / ".claude" / "settings.json",
        "cursor": home / ".cursor" / "hooks.json",
    }
    return paths[provider]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def _backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = path.with_name(f"{path.name}.8bit-buddy-{stamp}.bak")
    counter = 1
    while destination.exists():
        destination = path.with_name(f"{path.name}.8bit-buddy-{stamp}-{counter}.bak")
        counter += 1
    shutil.copy2(path, destination)
    return destination


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _backup(path)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def _command(executable: str, provider: str, config_path: Path | None = None) -> str:
    parts = [executable, "hook", provider]
    if config_path:
        parts.extend(("--config", str(config_path.expanduser().resolve())))
    return shlex.join(parts)


def _command_matches(value: object, provider: str) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parts = shlex.split(value)
    except ValueError:
        return False
    return any(
        Path(parts[index]).name == "8bit-buddy"
        and parts[index + 1 : index + 3] == ["hook", provider]
        for index in range(max(0, len(parts) - 2))
    )


def _install_nested_hook(data: dict[str, Any], provider: str, command: str) -> bool:
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("the existing 'hooks' value is not a JSON object")
    changed = False
    for event in HOOK_EVENTS[provider]:
        groups = hooks.setdefault(event, [])
        if not isinstance(groups, list):
            raise ValueError(f"the existing hooks.{event} value is not a JSON array")
        found = any(
            isinstance(group, dict)
            and any(
                isinstance(handler, dict) and _command_matches(handler.get("command"), provider)
                for handler in group.get("hooks", [])
            )
            for group in groups
        )
        if not found:
            groups.append(
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": command,
                            "timeout": 5,
                        }
                    ]
                }
            )
            changed = True
    return changed


def _install_cursor_hook(data: dict[str, Any], command: str) -> bool:
    data.setdefault("version", 1)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("the existing 'hooks' value is not a JSON object")
    changed = False
    for event in HOOK_EVENTS["cursor"]:
        handlers = hooks.setdefault(event, [])
        if not isinstance(handlers, list):
            raise ValueError(f"the existing hooks.{event} value is not a JSON array")
        if not any(
            isinstance(handler, dict) and _command_matches(handler.get("command"), "cursor")
            for handler in handlers
        ):
            handlers.append({"command": command, "timeout": 5})
            changed = True
    return changed


def install_hooks(
    providers: Iterable[str],
    *,
    executable: str | None = None,
    home: Path | None = None,
    config_path: Path | None = None,
) -> list[Path]:
    executable = executable or shutil.which("8bit-buddy")
    if not executable:
        raise FileNotFoundError("8bit-buddy is not on PATH")
    changed_paths: list[Path] = []
    for provider in providers:
        if provider not in HOOK_EVENTS:
            raise ValueError(f"unsupported provider: {provider}")
        path = hook_path(provider, home)
        data = _read_json(path)
        command = _command(str(Path(executable).expanduser().resolve()), provider, config_path)
        changed = (
            _install_cursor_hook(data, command)
            if provider == "cursor"
            else _install_nested_hook(data, provider, command)
        )
        if changed:
            _write_json(path, data)
            changed_paths.append(path)
    return changed_paths


def _remove_nested_hook(data: dict[str, Any], provider: str) -> bool:
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return False
    changed = False
    for event in HOOK_EVENTS[provider]:
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        retained_groups: list[Any] = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                retained_groups.append(group)
                continue
            handlers = group["hooks"]
            retained_handlers = [
                handler
                for handler in handlers
                if not (
                    isinstance(handler, dict) and _command_matches(handler.get("command"), provider)
                )
            ]
            if len(retained_handlers) != len(handlers):
                changed = True
            if retained_handlers:
                copy = dict(group)
                copy["hooks"] = retained_handlers
                retained_groups.append(copy)
        hooks[event] = retained_groups
    return changed


def _remove_cursor_hook(data: dict[str, Any]) -> bool:
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return False
    changed = False
    for event in HOOK_EVENTS["cursor"]:
        handlers = hooks.get(event)
        if not isinstance(handlers, list):
            continue
        retained = [
            handler
            for handler in handlers
            if not (
                isinstance(handler, dict) and _command_matches(handler.get("command"), "cursor")
            )
        ]
        if len(retained) != len(handlers):
            hooks[event] = retained
            changed = True
    return changed


def uninstall_hooks(providers: Iterable[str], *, home: Path | None = None) -> list[Path]:
    changed_paths: list[Path] = []
    for provider in providers:
        path = hook_path(provider, home)
        if not path.exists():
            continue
        data = _read_json(path)
        changed = (
            _remove_cursor_hook(data)
            if provider == "cursor"
            else _remove_nested_hook(data, provider)
        )
        if changed:
            _write_json(path, data)
            changed_paths.append(path)
    return changed_paths


def service_plist(executable: str, config_path: Path, home: Path | None = None) -> bytes:
    home = home or Path.home()
    logs = home / "Library" / "Logs"
    return plistlib.dumps(
        {
            "Label": SERVICE_LABEL,
            "ProgramArguments": [
                str(Path(executable).expanduser().resolve()),
                "serve",
                "--config",
                str(config_path.expanduser().resolve()),
            ],
            "RunAtLoad": True,
            "KeepAlive": True,
            "ProcessType": "Background",
            "StandardOutPath": str(logs / "8bitBuddy.log"),
            "StandardErrorPath": str(logs / "8bitBuddy.error.log"),
        },
        sort_keys=True,
    )


def service_path(home: Path | None = None) -> Path:
    home = home or Path.home()
    return home / "Library" / "LaunchAgents" / f"{SERVICE_LABEL}.plist"


def install_service(
    config_path: Path, *, executable: str | None = None, home: Path | None = None
) -> Path:
    if sys.platform != "darwin":
        raise OSError("launchd service installation is only supported on macOS")
    executable = executable or shutil.which("8bit-buddy")
    if not executable:
        raise FileNotFoundError("8bit-buddy is not on PATH")
    home = home or Path.home()
    path = service_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    (home / "Library" / "Logs").mkdir(parents=True, exist_ok=True)
    _backup(path)
    path.write_bytes(service_plist(executable, config_path, home))

    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", domain, str(path)], check=False)
    subprocess.run(["launchctl", "bootstrap", domain, str(path)], check=True)
    subprocess.run(["launchctl", "kickstart", "-k", f"{domain}/{SERVICE_LABEL}"], check=True)
    return path


def uninstall_service(*, home: Path | None = None) -> Path | None:
    if sys.platform != "darwin":
        raise OSError("launchd service removal is only supported on macOS")
    path = service_path(home)
    if not path.exists():
        return None
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", domain, str(path)], check=False)
    _backup(path)
    path.unlink()
    return path
