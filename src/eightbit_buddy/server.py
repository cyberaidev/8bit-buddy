from __future__ import annotations

import hmac
import json
import logging
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .config import AppConfig
from .display import DisplayBackend, build_display
from .model import AgentEvent
from .store import StateStore

MAX_BODY_BYTES = 64 * 1024


class BeaconServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, config: AppConfig, display: DisplayBackend | None = None) -> None:
        if config.server.host not in {"127.0.0.1", "localhost"}:
            raise ValueError("server.host must remain loopback-only")
        self.config = config
        self.display = display or build_display(config)
        self.store = StateStore(config.ttl)
        super().__init__((config.server.host, config.server.port), BeaconRequestHandler)

    def authorized(self, token: str) -> bool:
        expected = self.config.server.token
        return not expected or hmac.compare_digest(token, expected)

    def expire(self) -> None:
        log = logging.getLogger("eightbit_buddy.server")
        for record in self.store.pop_expired():
            try:
                self.display.delete(record)
            except OSError as exc:
                log.warning("could not remove expired AWTRIX app: %s", exc)


class BeaconRequestHandler(BaseHTTPRequestHandler):
    server: BeaconServer

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        logging.getLogger("eightbit_buddy.http").debug(format, *args)

    def _json(self, status: int, payload: object) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _authorized(self) -> bool:
        return self.server.authorized(self.headers.get("X-8bit-Buddy-Token", ""))

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorized():
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        if self.path == "/health":
            self._json(HTTPStatus.OK, {"status": "ok", "display": self.server.display.check()})
            return
        if self.path == "/v1/agents":
            self.server.expire()
            self._json(
                HTTPStatus.OK,
                {"agents": [record.to_dict() for record in self.server.store.list()]},
            )
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/events":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        if not self._authorized():
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY_BYTES:
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "invalid body size"})
            return
        try:
            raw = json.loads(self.rfile.read(length))
            event = AgentEvent.from_dict(raw)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": f"invalid event: {exc}"})
            return

        record = self.server.store.apply(event)
        if record is not None:
            try:
                self.server.display.show(record)
            except OSError as exc:
                logging.getLogger("eightbit_buddy.server").warning("display update failed: %s", exc)
        self._json(HTTPStatus.ACCEPTED, {"accepted": True})


def run_server(config: AppConfig, display: DisplayBackend | None = None) -> None:
    server = BeaconServer(config, display)
    stop = threading.Event()

    def housekeeper() -> None:
        while not stop.wait(1):
            server.expire()

    thread = threading.Thread(target=housekeeper, name="8bit-buddy-expiry", daemon=True)
    thread.start()
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        stop.set()
        server.server_close()
