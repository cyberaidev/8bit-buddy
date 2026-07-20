from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.error
import urllib.request
from contextlib import suppress
from pathlib import Path

from . import __version__
from .adapters import SUPPORTED_PROVIDERS, adapt_hook
from .client import send_event
from .config import (
    config_template,
    default_config_path,
    load_config,
    write_config,
)
from .installer import install_hooks, install_service, uninstall_hooks, uninstall_service
from .model import AgentEvent, AgentState
from .server import run_server


def _config_path(value: str | None) -> Path:
    return Path(value).expanduser() if value else default_config_path()


def _providers(values: list[str]) -> list[str]:
    return list(SUPPORTED_PROVIDERS) if "all" in values else values


def _get_json(path: str, config_path: Path) -> object:
    config = load_config(config_path)
    headers = {}
    if config.server.token:
        headers["X-8bit-Buddy-Token"] = config.server.token
    request = urllib.request.Request(
        f"http://{config.server.host}:{config.server.port}{path}", headers=headers
    )
    with urllib.request.urlopen(request, timeout=1.5) as response:
        return json.load(response)


def _hook(args: argparse.Namespace) -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            return 0
        event = adapt_hook(args.provider, payload, name_override=args.name)
        if event:
            send_event(event, load_config(_config_path(args.config)))
    except Exception:  # noqa: BLE001
        # Agent lifecycle hooks are observability only and always fail open.
        return 0
    return 0


def _emit(args: argparse.Namespace) -> int:
    event = AgentEvent(
        provider=args.provider,
        agent_key=args.key or f"{args.provider}:manual:{args.name}",
        name=args.name,
        state=AgentState(args.state),
        detail=args.detail,
        session_id="manual",
    )
    ok = send_event(event, load_config(_config_path(args.config)), timeout=1.5)
    if not ok:
        print("8bit Buddy service is not reachable.", file=sys.stderr)
        return 1
    return 0


def _demo(args: argparse.Namespace) -> int:
    config = load_config(_config_path(args.config))
    key = "demo:local:main"
    for state in (
        AgentState.RUNNING,
        AgentState.ATTENTION,
        AgentState.COMPLETE,
    ):
        event = AgentEvent("demo", key, args.name, state, session_id="demo")
        if not send_event(event, config, timeout=1.5):
            print("8bit Buddy service is not reachable.", file=sys.stderr)
            return 1
        if state != AgentState.COMPLETE:
            time.sleep(args.seconds)
    return 0


def _configure(args: argparse.Namespace) -> int:
    path = _config_path(args.config)
    if not args.console and not args.display_host:
        print("--display-host is required unless --console is used", file=sys.stderr)
        return 2
    try:
        write_config(
            path,
            config_template(args.display_host or "", console=args.console),
            force=args.force,
        )
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(path)
    return 0


def _serve(args: argparse.Namespace) -> int:
    config = load_config(_config_path(args.config))
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    print(f"8bit Buddy listening on {config.server.host}:{config.server.port}")
    with suppress(KeyboardInterrupt):
        run_server(config)
    return 0


def _status(args: argparse.Namespace) -> int:
    try:
        payload = _get_json("/v1/agents", _config_path(args.config))
    except (OSError, urllib.error.URLError) as exc:
        print(f"8bit Buddy service is not reachable: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    agents = payload.get("agents", []) if isinstance(payload, dict) else []
    if not agents:
        print("No active agents.")
        return 0
    for agent in agents:
        print(f"{agent['state']:>9}  {agent['name']}")
    return 0


def _health(args: argparse.Namespace) -> int:
    try:
        payload = _get_json("/health", _config_path(args.config))
    except (OSError, urllib.error.URLError) as exc:
        print(f"8bit Buddy service is not reachable: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2))
    return 0 if isinstance(payload, dict) and payload.get("display") else 1


def _install_hooks(args: argparse.Namespace) -> int:
    changed = install_hooks(_providers(args.providers), config_path=_config_path(args.config))
    if changed:
        print("Updated:")
        for path in changed:
            print(f"  {path}")
    else:
        print("Hooks are already installed.")
    if "codex" in _providers(args.providers):
        print("Codex only: open /hooks once and trust the new command hooks.")
    return 0


def _uninstall_hooks(args: argparse.Namespace) -> int:
    changed = uninstall_hooks(_providers(args.providers))
    for path in changed:
        print(f"Removed 8bit Buddy hooks from {path}")
    if not changed:
        print("No 8bit Buddy hooks found.")
    return 0


def _install_service(args: argparse.Namespace) -> int:
    path = install_service(_config_path(args.config))
    print(path)
    return 0


def _uninstall_service(_: argparse.Namespace) -> int:
    path = uninstall_service()
    print(f"Removed {path}" if path else "8bit Buddy service was not installed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="8bit-buddy",
        description="Physical status for Codex, Claude Code, and Cursor agents.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    configure = sub.add_parser("configure", help="create a local configuration file")
    configure.add_argument("--display-host", help="AWTRIX hostname or IP address")
    configure.add_argument("--console", action="store_true", help="log updates without hardware")
    configure.add_argument("--config")
    configure.add_argument("--force", action="store_true")
    configure.set_defaults(func=_configure)

    serve = sub.add_parser("serve", help="run the local status service")
    serve.add_argument("--config")
    serve.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR"), default="INFO")
    serve.set_defaults(func=_serve)

    hook = sub.add_parser("hook", help="internal adapter used by agent lifecycle hooks")
    hook.add_argument("provider", choices=SUPPORTED_PROVIDERS)
    hook.add_argument("--config")
    hook.add_argument("--name")
    hook.set_defaults(func=_hook)

    emit = sub.add_parser("emit", help="send one manual status event")
    emit.add_argument("--provider", default="demo")
    emit.add_argument("--name", required=True)
    emit.add_argument("--state", choices=tuple(state.value for state in AgentState), required=True)
    emit.add_argument("--detail", default="")
    emit.add_argument("--key")
    emit.add_argument("--config")
    emit.set_defaults(func=_emit)

    demo = sub.add_parser("demo", help="cycle through working, attention, and done")
    demo.add_argument("--name", default="8bit Buddy")
    demo.add_argument("--seconds", type=float, default=2.0)
    demo.add_argument("--config")
    demo.set_defaults(func=_demo)

    status = sub.add_parser("status", help="list active agents")
    status.add_argument("--json", action="store_true")
    status.add_argument("--config")
    status.set_defaults(func=_status)

    health = sub.add_parser("health", help="check the service and display")
    health.add_argument("--config")
    health.set_defaults(func=_health)

    install_hook_parser = sub.add_parser("install-hooks", help="merge global agent hooks safely")
    install_hook_parser.add_argument(
        "--providers", nargs="+", choices=(*SUPPORTED_PROVIDERS, "all"), default=["all"]
    )
    install_hook_parser.add_argument("--config")
    install_hook_parser.set_defaults(func=_install_hooks)

    uninstall_hook_parser = sub.add_parser("uninstall-hooks", help="remove only 8bit Buddy hooks")
    uninstall_hook_parser.add_argument(
        "--providers", nargs="+", choices=(*SUPPORTED_PROVIDERS, "all"), default=["all"]
    )
    uninstall_hook_parser.set_defaults(func=_uninstall_hooks)

    service = sub.add_parser("install-service", help="install and start the macOS LaunchAgent")
    service.add_argument("--config")
    service.set_defaults(func=_install_service)

    remove_service = sub.add_parser("uninstall-service", help="remove the macOS LaunchAgent")
    remove_service.set_defaults(func=_uninstall_service)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
