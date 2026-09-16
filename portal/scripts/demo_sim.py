"""Live demo simulator — streams realistic, moving telemetry to a demo tenant's devices so the
dashboards keep updating during demos. Occasionally crosses the seeded alert thresholds so alarms
fire. Runs as the `demo` compose profile; never run against real student tenants.

Env: TB_ADMIN_URL, TB_SYSADMIN_EMAIL/PASSWORD, DEMO_TENANT_EMAIL, DEMO_INTERVAL (seconds).
"""

from __future__ import annotations

# ruff: noqa: S311  (simulator randomness — not security-sensitive)
import math
import os
import random
import time

import httpx

TB = os.environ.get("TB_ADMIN_URL", "http://tb:8080").rstrip("/") + "/api"
EMAIL = os.environ.get("DEMO_TENANT_EMAIL", "major.student@chertiot.com")
INTERVAL = float(os.environ.get("DEMO_INTERVAL", "15"))


def h(tok: str) -> dict[str, str]:
    return {"X-Authorization": f"Bearer {tok}"}


def sysadmin_token(c: httpx.Client) -> str:
    r = c.post(
        f"{TB}/auth/login",
        json={
            "username": os.environ["TB_SYSADMIN_EMAIL"],
            "password": os.environ["TB_SYSADMIN_PASSWORD"],
        },
    )
    r.raise_for_status()
    return r.json()["token"]


def device_tokens(c: httpx.Client, systok: str) -> dict[str, str]:
    """Resolve {device_name: access_token} for the demo tenant via sysadmin impersonation."""
    tenants = c.get(
        f"{TB}/tenants?pageSize=200&page=0&textSearch={EMAIL}", headers=h(systok)
    ).json()["data"]
    tenant = next(t for t in tenants if t.get("title") == EMAIL)
    tid = tenant["id"]["id"]
    uid = c.get(f"{TB}/tenant/{tid}/users?pageSize=5&page=0", headers=h(systok)).json()["data"][0][
        "id"
    ]["id"]
    stok = c.get(f"{TB}/user/{uid}/token", headers=h(systok)).json()["token"]
    out: dict[str, str] = {}
    devs = c.get(f"{TB}/tenant/devices?pageSize=100&page=0", headers=h(stok)).json()["data"]
    for d in devs:
        did = d["id"]["id"]
        cred = c.get(f"{TB}/device/{did}/credentials", headers=h(stok)).json()
        out[d["name"]] = cred["credentialsId"]
    return out


def reading(name: str, t: float) -> dict[str, float] | None:
    """Realistic values; ~1-in-8 chance of crossing a seeded alert threshold."""
    hod = (t / 3600.0) % 24  # hour of day
    temp = 23 + 6 * math.sin((hod - 9) / 24 * 2 * math.pi) + random.uniform(-1, 1)
    spike = random.random() < 0.12
    if name == "greenhouse-sensor":
        return {
            "temperature": round(temp + (7 if spike else 0), 2),  # >30 fires
            "humidity": round(58 - 0.7 * (temp - 22) + random.uniform(-3, 3), 1),
            "soil_moisture": round(45 + 12 * math.sin(t / 900) + random.uniform(-4, 4), 1),
            "light_lux": round(max(0, 800 * math.sin((hod - 6) / 24 * 2 * math.pi))),
        }
    if name == "weather-station":
        return {
            "temperature": round(temp - 2, 2),
            "humidity": round(63 - 0.7 * (temp - 22) + random.uniform(-3, 3), 1),
            "pressure": round(1013 + random.uniform(-6, 6), 1),
            "wind_speed": round(abs(random.gauss(18 if spike else 8, 4)), 1),  # >15 fires
        }
    if name == "water-tank":
        return {
            # <25 fires the water-tank alarm
            "level_pct": round(20 if spike else (40 + 25 * abs(math.sin(t / 1800))), 1),
            "flow_lpm": round(abs(random.gauss(3, 2)), 2),
            "ph": round(6.8 + random.uniform(-0.3, 0.3), 2),
        }
    if name == "hvac-unit":
        return {
            "temperature": round(temp, 2),
            "setpoint": 24,
            "power_w": round(
                (950 if spike else max(0, (temp - 24) * 120)) + random.uniform(0, 40), 1
            ),
        }
    if name.startswith("lora-"):
        return {
            "temperature": round(21 + 3 * math.sin(t / 600) + random.uniform(-0.5, 0.5), 1),
            "battery": round(90 - (t % 100000) / 100000 * 5, 1),
            "rssi": random.randint(-110, -70),
        }
    return None


def main() -> int:
    print(f"[demo_sim] streaming to {EMAIL} every {INTERVAL}s via {TB}", flush=True)
    with httpx.Client(timeout=15) as c:
        tokens: dict[str, str] = {}
        last_refresh = 0.0
        while True:
            now = time.time()
            try:
                if now - last_refresh > 300 or not tokens:  # refresh tokens every 5 min
                    tokens = device_tokens(c, sysadmin_token(c))
                    last_refresh = now
                    print(f"[demo_sim] devices: {list(tokens)}", flush=True)
                for name, tok in tokens.items():
                    vals = reading(name, now)
                    if vals:
                        c.post(f"{TB}/v1/{tok}/telemetry", json=vals)
            except Exception as e:  # keep the loop alive across transient errors
                print(f"[demo_sim] iteration error: {e!r}", flush=True)
                tokens = {}
            time.sleep(INTERVAL)


if __name__ == "__main__":
    raise SystemExit(main())
