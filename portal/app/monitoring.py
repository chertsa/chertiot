"""v2 Project Monitoring — portal-native, ThingsBoard-REST, tenant-scoped (D13).

All reads go through the caller's impersonated project-tenant session, so isolation is the tenant
boundary (proven: cross-tenant alarm read → 404, ack → 403). TB call paths omit `/api` (the client
prepends it). A bounded, short-TTL, process-local cache coalesces polling; it stores DATA only and
is never an access boundary — the router checks membership BEFORE any cache lookup.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.tb_client import TbClient

# range token -> (seconds back, interval ms, aggregation)
RANGES: dict[str, tuple[int, int, str]] = {
    "1h": (3600, 60_000, "AVG"),
    "6h": (6 * 3600, 300_000, "AVG"),
    "24h": (24 * 3600, 1_800_000, "AVG"),
    "7d": (7 * 24 * 3600, 3 * 3_600_000, "AVG"),
}
DEFAULT_RANGE = "24h"
PREFERRED_KEYS = ("temperature", "humidity")  # highlighted only when actually present
_TS_KEYS = [
    "temperature",
    "humidity",
    "soil_moisture",
    "level_pct",
    "power_w",
    "wind_speed",
    "battery",
]


class DeviceRow(BaseModel):
    name: str
    label: str = ""
    active: bool = False
    last_seen: str | None = None
    reading: str = ""


class AlarmRow(BaseModel):
    id: str | None = None
    type: str | None = None
    severity: str = ""
    status: str = ""
    device: str = ""
    time: str = ""


class SeriesPoint(BaseModel):
    t: str
    v: float


class ServiceHealth(BaseModel):
    thingsboard_connectivity: Literal["ok", "degraded", "unknown"] = "unknown"
    node_red: Literal["ok", "stopped", "unknown"] = "unknown"


class MonitoringSnapshot(BaseModel):
    generated_at: str
    range: str
    selected_device: str | None = None
    selected_key: str | None = None
    available_devices: list[dict[str, str]] = []
    numeric_keys: list[str] = []
    latest_values: list[dict[str, str]] = []
    device_count: int = 0
    online_count: int = 0
    offline_count: int = 0
    max_devices: int | None = None
    alarm_active_count: int = 0
    devices: list[DeviceRow] = []
    active_alarms: list[AlarmRow] = []
    alarm_history: list[AlarmRow] = []
    series: dict[str, list[SeriesPoint]] = {}
    services: ServiceHealth = ServiceHealth()
    stale: bool = False
    degraded: list[str] = []


def _fmt(ms: Any, fmt: str = "%Y-%m-%d %H:%M") -> str | None:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, UTC).strftime(fmt)
    except (ValueError, TypeError):
        return None


def _devices(session: TbClient) -> tuple[int, int, list[DeviceRow], list[dict[str, str]]]:
    query = {
        "entityFilter": {"type": "entityType", "entityType": "DEVICE"},
        "pageLink": {
            "pageSize": 100,
            "page": 0,
            "sortOrder": {"key": {"type": "ENTITY_FIELD", "key": "name"}, "direction": "ASC"},
        },
        "entityFields": [
            {"type": "ENTITY_FIELD", "key": "name"},
            {"type": "ENTITY_FIELD", "key": "label"},
        ],
        "latestValues": [
            {"type": "ATTRIBUTE", "key": "active"},
            {"type": "ATTRIBUTE", "key": "lastActivityTime"},
            *[{"type": "TIME_SERIES", "key": k} for k in _TS_KEYS],
        ],
    }
    res = session._post("/entitiesQuery/find", query)  # noqa: SLF001
    items = res.get("data", []) if isinstance(res, dict) else []
    count = res.get("totalElements", len(items)) if isinstance(res, dict) else len(items)
    rows: list[DeviceRow] = []
    devices: list[dict[str, str]] = []
    online = 0
    for it in items:
        latest = it.get("latest", {})
        fields = latest.get("ENTITY_FIELD", {})
        attrs = latest.get("ATTRIBUTE", {})
        tsv = latest.get("TIME_SERIES", {})
        name = (fields.get("name") or {}).get("value", "?")
        did = (it.get("entityId") or {}).get("id")
        active = str((attrs.get("active") or {}).get("value", "")).lower() == "true"
        online += 1 if active else 0
        reading = ", ".join(
            f"{k} {tsv[k]['value']}"
            for k in _TS_KEYS
            if k in tsv and tsv[k].get("value") not in (None, "")
        )
        rows.append(
            DeviceRow(
                name=name,
                label=(fields.get("label") or {}).get("value", ""),
                active=active,
                last_seen=_fmt((attrs.get("lastActivityTime") or {}).get("value")),
                reading=reading[:60],
            )
        )
        if did:
            devices.append({"id": did, "name": name})
    return count, online, rows, devices


def _alarms(session: TbClient, status: str | None, limit: int) -> list[AlarmRow]:
    params: dict[str, Any] = {
        "pageSize": limit,
        "page": 0,
        "sortProperty": "createdTime",
        "sortOrder": "DESC",
    }
    if status:
        params["searchStatus"] = status
    data = session._get("/alarms", **params)  # noqa: SLF001
    rows = data.get("data", []) if isinstance(data, dict) else []
    return [
        AlarmRow(
            id=(a.get("id") or {}).get("id"),
            type=a.get("type"),
            severity=a.get("severity", ""),
            status=a.get("status", ""),
            device=a.get("originatorName", ""),
            time=_fmt(a.get("createdTime", 0), "%Y-%m-%d %H:%M") or "",
        )
        for a in rows
    ]


def _numeric_keys_and_latest(
    session: TbClient, device_id: str
) -> tuple[list[str], list[dict[str, str]]]:
    """Discover the device's numeric time-series keys and their latest values (one TB call)."""
    keys = session._get(f"/plugins/telemetry/DEVICE/{device_id}/keys/timeseries")  # noqa: SLF001
    if not isinstance(keys, list) or not keys:
        return [], []
    latest = session.latest_timeseries(device_id, list(keys))
    numeric: list[str] = []
    values: list[dict[str, str]] = []
    for k in keys:
        v = latest.get(k)
        if not v:
            continue
        val = v[0].get("value")
        try:
            float(val)  # type: ignore[arg-type]  # non-numeric/None → excluded below
            numeric.append(k)
            values.append({"key": k, "value": str(val), "t": _fmt(v[0].get("ts")) or ""})
        except (ValueError, TypeError, KeyError):
            pass
    return numeric, values


def _series(session: TbClient, device_id: str, key: str, rng: str) -> list[SeriesPoint]:
    back, interval, agg = RANGES[rng]
    end = int(time.time() * 1000)
    data = session._get(  # noqa: SLF001
        f"/plugins/telemetry/DEVICE/{device_id}/values/timeseries",
        keys=key,
        startTs=end - back * 1000,
        endTs=end,
        interval=interval,
        agg=agg,
        limit=1000,
    )
    pts = sorted((data or {}).get(key, []), key=lambda p: p["ts"]) if isinstance(data, dict) else []
    out: list[SeriesPoint] = []
    for p in pts:
        if p.get("value") is None:
            continue
        try:
            out.append(SeriesPoint(t=_fmt(p["ts"], "%m-%d %H:%M") or "", v=float(p["value"])))
        except (ValueError, TypeError):
            pass
    return out


def snapshot(
    sysadmin: TbClient,
    session: TbClient,
    tb_tenant_id: str | None,
    rng: str,
    device: str | None,
    key: str | None,
    node_red: str,
) -> MonitoringSnapshot:
    """Compose one tenant-scoped snapshot. Partial failures degrade a section, never raise."""
    rng = rng if rng in RANGES else DEFAULT_RANGE
    snap = MonitoringSnapshot(
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"), range=rng
    )
    services = ServiceHealth(node_red=node_red)

    try:
        snap.device_count, snap.online_count, snap.devices, snap.available_devices = _devices(
            session
        )
        snap.offline_count = max(snap.device_count - snap.online_count, 0)
        services.thingsboard_connectivity = "ok"
    except Exception:  # noqa: BLE001
        snap.degraded.append("devices")
        services.thingsboard_connectivity = "degraded"

    ids = {d["id"] for d in snap.available_devices}
    sel = (
        device
        if device in ids
        else (snap.available_devices[0]["id"] if snap.available_devices else None)
    )
    snap.selected_device = sel
    if sel:
        try:
            snap.numeric_keys, snap.latest_values = _numeric_keys_and_latest(session, sel)
        except Exception:  # noqa: BLE001
            snap.degraded.append("keys")
        selkey = (
            key
            if key in snap.numeric_keys
            else next(
                (k for k in PREFERRED_KEYS if k in snap.numeric_keys),
                snap.numeric_keys[0] if snap.numeric_keys else None,
            )
        )
        snap.selected_key = selkey
        if selkey:
            try:
                snap.series = {selkey: _series(session, sel, selkey, rng)}
            except Exception:  # noqa: BLE001
                snap.degraded.append("series")

    try:
        snap.active_alarms = _alarms(session, "ACTIVE", 10)
        snap.alarm_active_count = len(snap.active_alarms)
    except Exception:  # noqa: BLE001
        snap.degraded.append("alarms")
    try:
        snap.alarm_history = _alarms(session, None, 30)
    except Exception:  # noqa: BLE001
        snap.degraded.append("alarm_history")

    try:
        from app.routers.devices import _max_devices

        snap.max_devices = _max_devices(sysadmin, tb_tenant_id)
    except Exception:  # noqa: BLE001,S110
        pass

    snap.services = services
    return snap


# --- bounded, process-local TTL cache (data only; never an access boundary) -----------------------
_CACHE: dict[tuple[str, str, str, str], tuple[float, MonitoringSnapshot]] = {}
_CACHE_MAX = 256


def cached_snapshot(
    ttl: float, cache_key: tuple[str, str, str, str], builder: Callable[[], MonitoringSnapshot]
) -> MonitoringSnapshot:
    """Return a cached snapshot within `ttl` seconds, else build+store one. ttl<=0 disables caching.
    The caller MUST have authorised membership before calling this."""
    if ttl <= 0:
        return builder()
    now = time.time()
    hit = _CACHE.get(cache_key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    snap = builder()
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(min(_CACHE, key=lambda k: _CACHE[k][0]), None)
    _CACHE[cache_key] = (now, snap)
    return snap


def invalidate(project_id: str) -> None:
    for k in [k for k in _CACHE if k[0] == project_id]:
        _CACHE.pop(k, None)
