"""CHERT IoT notebook helper: fetch YOUR telemetry with your own ThingsBoard session (TB_JWT).

    import chertiot
    chertiot.devices()                          # your devices
    df = chertiot.telemetry("my-first-device", keys=["temperature"], hours=24)
    df.plot()
"""

from __future__ import annotations

import os
import time

import pandas as pd
import requests

TB = os.environ.get("TB_URL", "http://tb:8080").rstrip("/")
_HDR = {"X-Authorization": f"Bearer {os.environ.get('TB_JWT', '')}"}


def _get(path: str, **params):
    r = requests.get(f"{TB}/api{path}", headers=_HDR, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def devices() -> pd.DataFrame:
    rows = _get("/tenant/devices", pageSize=100, page=0)["data"]
    return pd.DataFrame([{"name": d["name"], "id": d["id"]["id"], "type": d["type"]} for d in rows])


def _device_id(name: str) -> str:
    return _get("/tenant/devices", deviceName=name)["id"]["id"]


def telemetry(device: str, keys: list[str], hours: float = 24) -> pd.DataFrame:
    """Timeseries for your device as a tidy DataFrame indexed by timestamp."""
    end = int(time.time() * 1000)
    start = end - int(hours * 3600 * 1000)
    raw = _get(
        f"/plugins/telemetry/DEVICE/{_device_id(device)}/values/timeseries",
        keys=",".join(keys), startTs=start, endTs=end, limit=50000, agg="NONE",
    )
    frames = []
    for key, points in raw.items():
        df = pd.DataFrame(points)
        if df.empty:
            continue
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        frames.append(df.set_index("ts")["value"].rename(key))
    return pd.concat(frames, axis=1).sort_index() if frames else pd.DataFrame()
