"""Configure Uptime Kuma fully via its socket.io API (M2.3 follow-up): admin account, a monitor
for every public service, and a published public status page. Idempotent — safe to rerun.

    KUMA_URL=http://uptime-kuma:3001 KUMA_PASSWORD=... DOMAIN=chertiot.com \
        uv run python -m scripts.setup_status_page
"""

from __future__ import annotations

import os
import sys
import time

import socketio

KUMA = os.environ.get("KUMA_URL", "http://uptime-kuma:3001")
USER = os.environ.get("KUMA_ADMIN", "chertiotadmin")
PASSWORD = os.environ["KUMA_PASSWORD"]
DOMAIN = os.environ["DOMAIN"]

MONITORS = [
    ("Portal", f"https://{DOMAIN}/healthz"),
    ("Dashboards (ThingsBoard)", f"https://app.{DOMAIN}/login"),
    ("Sign-in (Keycloak)", f"https://auth.{DOMAIN}/realms/chertiot"),
    ("Docs", f"https://{DOMAIN}/docs/"),
    ("Notebooks (JupyterHub)", f"https://lab.{DOMAIN}/hub/login"),
    ("Flows (Node-RED)", f"https://flows.{DOMAIN}"),
]


def _call(sio: socketio.Client, event: str, *args: object, timeout: float = 20) -> object:
    box: dict[str, object] = {}
    done = {"v": False}

    def cb(res: object) -> None:
        box["res"] = res
        done["v"] = True

    sio.emit(event, *args, callback=cb)
    end = time.time() + timeout
    while not done["v"] and time.time() < end:
        sio.sleep(0.1)
    return box.get("res")


def main() -> int:
    sio = socketio.Client(reconnection=False)
    ready = {"v": False}
    sio.on("connect", lambda: ready.__setitem__("v", True))
    # Kuma emits initial events; we don't need them.
    for noisy in (
        "monitorList",
        "heartbeatList",
        "importantHeartbeatList",
        "avgPing",
        "uptime",
        "info",
    ):
        sio.on(noisy, lambda *a: None)
    sio.connect(KUMA, transports=["websocket"], wait_timeout=20)
    for _ in range(50):
        if ready["v"]:
            break
        sio.sleep(0.1)

    need_setup = _call(sio, "needSetup")
    if need_setup:
        _call(sio, "setup", USER, PASSWORD)
        print("kuma: admin created")
    login = _call(sio, "login", {"username": USER, "password": PASSWORD, "token": ""})
    if not isinstance(login, dict) or not login.get("ok"):
        print(f"kuma login failed: {login}", file=sys.stderr)
        return 1
    print("kuma: logged in")

    existing = _call(sio, "getMonitorList")
    have = (
        {m.get("name") for m in (existing or {}).values()} if isinstance(existing, dict) else set()
    )
    ids: list[int] = []
    for name, url in MONITORS:
        if name in have:
            for mid, m in (existing or {}).items():  # type: ignore[union-attr]
                if m.get("name") == name:
                    ids.append(int(mid))
            continue
        res = _call(
            sio,
            "add",
            {
                "type": "http",
                "name": name,
                "url": url,
                "method": "GET",
                "interval": 60,
                "retryInterval": 60,
                "maxretries": 2,
                "accepted_statuscodes": ["200-399"],
                "ignoreTls": False,
                "upsideDown": False,
            },
        )
        if isinstance(res, dict) and res.get("ok"):
            ids.append(int(res["monitorID"]))
            print(f"kuma: monitor '{name}'")
    time.sleep(1)

    status = {
        "slug": "chert-iot",
        "title": "CHERT IoT status",
        "description": "Live availability of the CHERT IoT platform.",
        "theme": "auto",
        "published": True,
        "showTags": False,
        "domainNameList": [f"status.{DOMAIN}"],
        "footerText": "CHERT IoT",
        "showPoweredBy": False,
    }
    save = _call(sio, "getStatusPage", "chert-iot")
    if not (isinstance(save, dict) and save.get("ok")):
        _call(sio, "addStatusPage", "CHERT IoT status", "chert-iot")
        print("kuma: status page created")
    public = [{"name": "Platform", "monitorList": [{"id": i} for i in ids]}]
    _call(sio, "saveStatusPage", "chert-iot", status, [], public)
    print(f"kuma: status page published with {len(ids)} monitors")
    sio.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
