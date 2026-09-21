"""v2 Project Monitoring: flag guard + snapshot composition (fake TB session; no stack).
Cross-project isolation is the require_membership gate (403, proven for flows) plus the TB tenant
boundary (spike-proven: cross-tenant read 404, ack 403) — exercised on staging with the flag on.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app import monitoring


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


def test_snapshot_composition_and_numeric_filter() -> None:
    fake = FakeSession()
    snap = monitoring.snapshot(fake, fake, "tid", "24h", None, None, "ok")  # type: ignore[arg-type]
    assert snap.device_count == 2 and snap.online_count == 1 and snap.offline_count == 1
    assert [d["id"] for d in snap.available_devices] == ["dev1", "dev2"]
    assert "temperature" in snap.numeric_keys and "humidity" in snap.numeric_keys
    assert "note" not in snap.numeric_keys  # non-numeric excluded from charts
    assert snap.selected_key == "temperature"  # preferred key present
    assert snap.series["temperature"] and len(snap.series["temperature"]) == 2
    assert snap.alarm_active_count == 1 and snap.active_alarms[0].id == "al1"
    assert snap.services.thingsboard_connectivity == "ok"


def test_snapshot_bad_range_clamps() -> None:
    snap = monitoring.snapshot(FakeSession(), FakeSession(), "tid", "bogus", None, None, "unknown")  # type: ignore[arg-type]
    assert snap.range == monitoring.DEFAULT_RANGE
