"""Render firmware starter files from firmware-examples/ with a device's values (M1.2)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import Settings, get_settings

REPO_FIRMWARE_DIR = Path(__file__).resolve().parents[2] / "firmware-examples"


@dataclass(frozen=True)
class Track:
    key: str
    title: str
    path: str  # relative to firmware dir
    filename: str  # download name
    language: str  # for <code class="language-...">


TRACKS: dict[str, Track] = {
    "esp32-arduino": Track(
        "esp32-arduino",
        "ESP32 — Arduino",
        "esp32-arduino/chertiot_starter.ino",
        "chertiot_starter.ino",
        "cpp",
    ),
    "esp32-micropython": Track(
        "esp32-micropython", "ESP32 — MicroPython", "esp32-micropython/main.py", "main.py", "python"
    ),
    "rpi-python": Track(
        "rpi-python",
        "Raspberry Pi — Python",
        "rpi-python/chertiot_starter.py",
        "chertiot_starter.py",
        "python",
    ),
    "browser-js": Track(
        "browser-js", "Browser — no hardware", "browser-js/index.html", "index.html", "html"
    ),
}


def firmware_dir(settings: Settings | None = None) -> Path:
    s = settings or get_settings()
    return Path(s.firmware_dir) if s.firmware_dir else REPO_FIRMWARE_DIR


def placeholders(
    device_name: str, access_token: str, settings: Settings | None = None
) -> dict[str, str]:
    s = settings or get_settings()
    return {
        "MQTT_HOST": s.device_mqtt_host,
        "MQTT_PORT": str(s.mqtt_port),
        "HTTP_URL": s.tb_public_url.rstrip("/"),
        "ACCESS_TOKEN": access_token,
        "DEVICE_NAME": device_name,
    }


def render(
    track: str, device_name: str, access_token: str, settings: Settings | None = None
) -> str:
    t = TRACKS[track]
    text = (firmware_dir(settings) / t.path).read_text()
    for key, value in placeholders(device_name, access_token, settings).items():
        text = text.replace("{{" + key + "}}", value)
    return text
