"""Live project dashboard data, gathered from a project tenant in a few REST calls (one Entity Data
Query for devices+status+latest, one alarms call, one chart call) to stay under the rate limit."""

from __future__ import annotations

import json
import time as _time
from datetime import UTC, datetime
from typing import Any

from app.tb_client import TbClient

# Common numeric telemetry keys surfaced on the dashboard (one Entity Data Query, not N calls).
_TS_KEYS = [
    "temperature",
    "humidity",
    "soil_moisture",
    "level_pct",
    "power_w",
    "wind_speed",
    "battery",
]
_max_devices_cache: dict[str, Any] = {"ts": 0.0, "value": None}


def alarm_history(session: TbClient, limit: int = 30) -> list[dict[str, Any]]:
    """Recent alarms (any status) for the project's report — newest first, best-effort."""
    try:
        data = session._get(  # noqa: SLF001
            "/alarms",
            pageSize=limit,
            page=0,
            sortProperty="createdTime",
            sortOrder="DESC",
        )
    except Exception:  # noqa: BLE001
        return []
    rows = data.get("data", []) if isinstance(data, dict) else []
    out = []
    for a in rows:
        out.append(
            {
                "type": a.get("type"),
                "severity": a.get("severity", ""),
                "status": a.get("status", ""),
                "device": a.get("originatorName", ""),
                "time": datetime.fromtimestamp(a.get("createdTime", 0) / 1000, UTC).strftime(
                    "%Y-%m-%d %H:%M"
                ),
            }
        )
    return out


def dashboard_data(sysadmin: TbClient, session: TbClient) -> dict[str, Any]:
    """Live metrics for one project tenant. Defensive: partial failures degrade, never raise."""
    out: dict[str, Any] = {
        "device_count": 0,
        "online_count": 0,
        "max_devices": None,
        "alarm_count": 0,
        "devices": [],
        "alarms": [],
        "chart": None,
    }
    query = {
        "entityFilter": {"type": "entityType", "entityType": "DEVICE"},
        "pageLink": {
            "pageSize": 30,
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
    try:
        res = session._post("/entitiesQuery/find", query)  # noqa: SLF001 - typed client session
    except Exception:  # noqa: BLE001
        return out
    items = res.get("data", []) if isinstance(res, dict) else []
    out["device_count"] = (
        res.get("totalElements", len(items)) if isinstance(res, dict) else len(items)
    )
    rows: list[dict[str, Any]] = []
    online = 0
    chart_did = None
    for it in items[:12]:
        latest = it.get("latest", {})
        fields = latest.get("ENTITY_FIELD", {})
        attrs = latest.get("ATTRIBUTE", {})
        tsv = latest.get("TIME_SERIES", {})
        name = (fields.get("name") or {}).get("value", "?")
        active = str((attrs.get("active") or {}).get("value", "")).lower() == "true"
        online += 1 if active else 0
        last_seen = None
        lt = (attrs.get("lastActivityTime") or {}).get("value")
        if lt:
            try:
                last_seen = datetime.fromtimestamp(int(lt) / 1000, UTC).strftime("%Y-%m-%d %H:%M")
            except Exception:  # noqa: S110
                pass
        reading = ", ".join(
            f"{k} {tsv[k]['value']}"
            for k in _TS_KEYS
            if k in tsv and tsv[k].get("value") not in (None, "")
        )
        did = (it.get("entityId") or {}).get("id")
        rows.append(
            {
                "name": name,
                "label": (fields.get("label") or {}).get("value", ""),
                "active": active,
                "last_seen": last_seen,
                "reading": reading[:60],
            }
        )
        if chart_did is None and did and ("temperature" in tsv or "humidity" in tsv):
            chart_did = did
    out["devices"] = rows
    out["online_count"] = online

    now = _time.time()
    if now - _max_devices_cache["ts"] > 600:
        try:
            from app.routers.devices import _max_devices

            tid = None
            devs = session.list_devices()
            if devs and devs[0].tenant_id:
                tid = devs[0].tenant_id.id
            _max_devices_cache.update(ts=now, value=_max_devices(sysadmin, tid))
        except Exception:  # noqa: S110
            pass
    out["max_devices"] = _max_devices_cache["value"]

    try:
        data = session._get(  # noqa: SLF001
            "/alarms",
            pageSize=10,
            page=0,
            searchStatus="ACTIVE",
            sortProperty="createdTime",
            sortOrder="DESC",
        )
        alarms = data.get("data", []) if isinstance(data, dict) else []
        out["alarm_count"] = len(alarms)
        out["alarms"] = [
            {
                "type": a.get("type"),
                "severity": a.get("severity", ""),
                "device": a.get("originatorName", ""),
                "time": datetime.fromtimestamp(a.get("createdTime", 0) / 1000, UTC).strftime(
                    "%H:%M"
                ),
            }
            for a in alarms
        ]
    except Exception:  # noqa: S110 - alarms are optional
        pass

    if chart_did:
        try:
            end = int(_time.time() * 1000)
            ts = session._get(  # noqa: SLF001
                f"/plugins/telemetry/DEVICE/{chart_did}/values/timeseries",
                keys="temperature,humidity",
                startTs=end - 24 * 3600 * 1000,
                endTs=end,
                interval=1800000,
                agg="AVG",
                limit=50,
            )
            ts = ts if isinstance(ts, dict) else {}
            series = {}
            for key in ("temperature", "humidity"):
                pts = sorted(ts.get(key, []), key=lambda p: p["ts"])
                series[key] = [
                    {
                        "t": datetime.fromtimestamp(p["ts"] / 1000, UTC).strftime("%H:%M"),
                        "v": float(p["value"]),
                    }
                    for p in pts
                    if p.get("value") is not None
                ]
            if series.get("temperature") or series.get("humidity"):
                out["chart"] = json.dumps(series)
        except Exception:  # noqa: S110 - chart is optional
            pass
    return out
