"""v2 Project Monitoring: flag guard + snapshot composition (fake TB session; no stack).
Cross-project isolation is the require_membership gate (403, proven for flows) plus the TB tenant
boundary (spike-proven: cross-tenant read 404, ack 403) — exercised on staging with the flag on.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import monitoring
from app.config import get_settings


@pytest.fixture
def flags_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """Turn the v2 flags on for the duration of a test (settings is a cached singleton)."""
    s = get_settings()
    monkeypatch.setattr(s, "monitoring_enabled", True)
    monkeypatch.setattr(s, "telemetry_enabled", True)


class FakeSession:
    """Minimal TbClient stand-in returning canned tenant-scoped data."""

    def _post(self, path: str, body: Any = None, **kw: Any) -> Any:
        if path == "/entitiesQuery/find":
            return {
                "totalElements": 2,
                "data": [
                    {
                        "entityId": {"id": "dev1"},
                        "latest": {
                            "ENTITY_FIELD": {"name": {"value": "d1"}},
                            "ATTRIBUTE": {
                                "active": {"value": "true"},
                                "lastActivityTime": {"value": "1690000000000"},
                            },
                            "TIME_SERIES": {"temperature": {"value": "21"}},
                        },
                    },
                    {
                        "entityId": {"id": "dev2"},
                        "latest": {
                            "ENTITY_FIELD": {"name": {"value": "d2"}},
                            "ATTRIBUTE": {"active": {"value": "false"}},
                            "TIME_SERIES": {},
                        },
                    },
                ],
            }
        return {}

    def _get(self, path: str, **kw: Any) -> Any:
        if path == "/alarms":
            return {
                "data": [
                    {
                        "id": {"id": "al1"},
                        "type": "T",
                        "severity": "CRITICAL",
                        "status": "ACTIVE_UNACK",
                        "originatorName": "d1",
                        "createdTime": 1690000000000,
                    }
                ]
            }
        if "keys/timeseries" in path:
            return ["temperature", "humidity", "note"]
        if "values/timeseries" in path:
            if kw.get("agg") == "COUNT":  # per-device activity (data-point counts)
                return {
                    "temperature": [{"ts": 1, "value": "3"}, {"ts": 2, "value": "4"}],
                    "humidity": [{"ts": 1, "value": "3"}, {"ts": 2, "value": "4"}],
                }
            return {
                "temperature": [
                    {"ts": 1690000000000, "value": "21.5"},
                    {"ts": 1690000600000, "value": "22.0"},
                ]
            }
        return {}

    def latest_timeseries(self, device_id: str, keys: list[str]) -> Any:
        return {
            "temperature": [{"ts": 1, "value": "21"}],
            "humidity": [{"ts": 1, "value": "50"}],
            "note": [{"ts": 1, "value": "hello"}],  # non-numeric → excluded
        }


def test_monitoring_flag_off_is_404(client: TestClient) -> None:
    # ships dark: routes return 404 until MONITORING_ENABLED is on
    assert client.get("/projects/x/monitoring").status_code == 404
    assert client.get("/projects/x/monitoring/data").status_code == 404
    assert client.post("/projects/x/monitoring/alarms/a/ack").status_code == 404


def test_telemetry_flag_off_is_404(client: TestClient) -> None:
    # ships dark: the telemetry tab is 404 until TELEMETRY_ENABLED is on
    assert client.get("/projects/x/telemetry").status_code == 404


def test_data_and_ack_require_authentication(client: TestClient, flags_on: None) -> None:
    # flag on, but no session → API endpoints answer 401 (not a redirect to /login)
    assert client.get("/projects/x/monitoring/data").status_code == 401
    assert client.post("/projects/x/monitoring/alarms/a/ack").status_code == 401


def test_non_member_is_forbidden(
    client: TestClient, flags_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    # a signed-in user who is not a member of the project gets 403, never someone else's data
    user = SimpleNamespace(id="u1", email="stranger@chertiot.dev")
    monkeypatch.setattr("app.project.load_user", lambda request, db: user)
    assert client.get("/projects/x/monitoring/data").status_code == 403
    assert client.post("/projects/x/monitoring/alarms/a/ack").status_code == 403


def test_snapshot_composition_and_numeric_filter() -> None:
    fake = FakeSession()
    snap = monitoring.snapshot(fake, fake, "tid", "24h", None, None, "ok")  # type: ignore[arg-type]
    assert snap.device_count == 2 and snap.online_count == 1 and snap.offline_count == 1
    assert [d["id"] for d in snap.available_devices] == ["dev1", "dev2"]
    assert "temperature" in snap.numeric_keys and "humidity" in snap.numeric_keys
    assert "note" not in snap.numeric_keys  # non-numeric excluded from charts
    assert snap.selected_key == "temperature"  # preferred key present
    latest = {v["key"]: v["value"] for v in snap.latest_values}
    assert latest == {"temperature": "21", "humidity": "50"}  # numeric only; 'note' excluded
    assert snap.series["temperature"] and len(snap.series["temperature"]) == 2
    assert snap.alarm_active_count == 1 and snap.active_alarms[0].id == "al1"
    assert snap.services.thingsboard_connectivity == "ok"


def test_snapshot_activity_per_device() -> None:
    fake = FakeSession()
    snap = monitoring.snapshot(fake, fake, "tid", "24h", None, None, "ok", with_activity=True)  # type: ignore[arg-type]
    # per-device data-point totals (COUNT across keys): temperature 3 + humidity 3 = 6
    totals = {a["name"]: a["points"] for a in snap.activity}
    assert totals == {"d1": "6", "d2": "6"}
    assert snap.activity[0]["online"] == "true"  # d1 active
    # selected device's throughput trend has per-interval buckets (ts1=6, ts2=8)
    assert [p.v for p in snap.activity_series] == [6.0, 8.0]


def test_snapshot_activity_off_by_default() -> None:
    fake = FakeSession()
    snap = monitoring.snapshot(fake, fake, "tid", "24h", None, None, "ok")  # type: ignore[arg-type]
    assert snap.activity == [] and snap.activity_series == []  # Monitoring path unaffected


def test_snapshot_bad_range_clamps() -> None:
    snap = monitoring.snapshot(FakeSession(), FakeSession(), "tid", "bogus", None, None, "unknown")  # type: ignore[arg-type]
    assert snap.range == monitoring.DEFAULT_RANGE
