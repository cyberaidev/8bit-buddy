from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import AppConfig
from .model import AgentEvent


def send_event(event: AgentEvent, config: AppConfig, *, timeout: float = 0.6) -> bool:
    url = f"http://{config.server.host}:{config.server.port}/v1/events"
    headers = {"Content-Type": "application/json"}
    if config.server.token:
        headers["X-8bit-Buddy-Token"] = config.server.token
    request = urllib.request.Request(
        url,
        data=json.dumps(event.to_dict()).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (OSError, urllib.error.URLError):
        # Hooks must fail open: an unavailable desk display must never stall an agent.
        return False
