from __future__ import annotations

import os
import secrets
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ServerSettings:
    host: str = "127.0.0.1"
    port: int = 7391
    token: str = ""


@dataclass(frozen=True, slots=True)
class DisplaySettings:
    driver: str = "console"
    host: str = ""
    timeout_seconds: float = 1.5
    app_prefix: str = "8bitbuddy"
    scroll_speed: int = 85


@dataclass(frozen=True, slots=True)
class TTLSettings:
    running: int = 14_400
    attention: int = 3_600
    complete: int = 120
    error: int = 3_600


@dataclass(frozen=True, slots=True)
class ColorSettings:
    running: str = "#2196F3"
    attention: str = "#FF1744"
    complete: str = "#00E676"
    error: str = "#FF1744"
    background: str = "#000000"


@dataclass(frozen=True, slots=True)
class AppConfig:
    server: ServerSettings = field(default_factory=ServerSettings)
    display: DisplaySettings = field(default_factory=DisplaySettings)
    ttl: TTLSettings = field(default_factory=TTLSettings)
    colors: ColorSettings = field(default_factory=ColorSettings)


def default_config_path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "8bit-buddy" / "config.toml"


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    return value if isinstance(value, dict) else {}


def load_config(path: Path | None = None) -> AppConfig:
    path = path or default_config_path()
    if not path.exists():
        return AppConfig()
    with path.open("rb") as handle:
        data = tomllib.load(handle)

    server = _section(data, "server")
    display = _section(data, "display")
    ttl = _section(data, "ttl")
    colors = _section(data, "colors")
    return AppConfig(
        server=ServerSettings(
            host=str(server.get("host", "127.0.0.1")),
            port=int(server.get("port", 7391)),
            token=str(server.get("token", "")),
        ),
        display=DisplaySettings(
            driver=str(display.get("driver", "console")),
            host=str(display.get("host", "")),
            timeout_seconds=float(display.get("timeout_seconds", 1.5)),
            app_prefix=str(display.get("app_prefix", "8bitbuddy")),
            scroll_speed=int(display.get("scroll_speed", 85)),
        ),
        ttl=TTLSettings(
            running=int(ttl.get("running", 14_400)),
            attention=int(ttl.get("attention", 3_600)),
            complete=int(ttl.get("complete", 120)),
            error=int(ttl.get("error", 3_600)),
        ),
        colors=ColorSettings(
            running=str(colors.get("running", "#2196F3")),
            attention=str(colors.get("attention", "#FF1744")),
            complete=str(colors.get("complete", "#00E676")),
            error=str(colors.get("error", "#FF1744")),
            background=str(colors.get("background", "#000000")),
        ),
    )


def config_template(display_host: str, *, console: bool = False) -> str:
    driver = "console" if console else "awtrix"
    token = secrets.token_urlsafe(24)
    return f'''# 8bit Buddy configuration
[server]
host = "127.0.0.1"
port = 7391
token = "{token}"

[display]
driver = "{driver}"
host = "{display_host}"
timeout_seconds = 1.5
app_prefix = "8bitbuddy"
scroll_speed = 85

[ttl]
running = 14400
attention = 3600
complete = 120
error = 3600

[colors]
running = "#2196F3"
attention = "#FF1744"
complete = "#00E676"
error = "#FF1744"
background = "#000000"
'''


def write_config(path: Path, content: str, *, force: bool = False) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"configuration already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.chmod(0o600)
    temporary.replace(path)
