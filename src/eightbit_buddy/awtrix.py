from __future__ import annotations

import json
import threading
import urllib.parse
import urllib.request
from typing import Any


class AwtrixClient:
    """Small AWTRIX 3 HTTP client shared by agent and sit/stand displays."""

    def __init__(self, host: str, *, timeout: float = 1.5) -> None:
        base = host.strip().rstrip("/")
        if not base:
            raise ValueError("display.host is required")
        self.base_url = base if "://" in base else f"http://{base}"
        self.timeout = timeout
        self._lock = threading.Lock()

    def _request(
        self,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        data: bytes | None = None,
        method: str = "POST",
    ) -> None:
        body = data if data is not None else json.dumps(payload or {}).encode()
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body if method != "GET" else None,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        with self._lock, urllib.request.urlopen(request, timeout=self.timeout):
            pass

    def custom_app(self, name: str, payload: dict[str, Any]) -> None:
        safe_name = urllib.parse.quote(name, safe="")
        self._request(f"/api/custom?name={safe_name}", payload=payload)

    def delete_custom_app(self, name: str) -> None:
        safe_name = urllib.parse.quote(name, safe="")
        self._request(f"/api/custom?name={safe_name}", data=b"")

    def notify(self, payload: dict[str, Any]) -> None:
        self._request("/api/notify", payload=payload)

    def check(self) -> bool:
        try:
            self._request("/api/stats", method="GET")
        except OSError:
            return False
        return True
