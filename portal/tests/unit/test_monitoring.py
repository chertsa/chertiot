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
    # total = sum of per-interval buckets: (temp3+hum3)=6 at ts1 + (temp4+hum4)=8 at ts2 = 14
    totals = {a.name: a.data_points for a in snap.activity}
    assert totals == {"d1": 14, "d2": 14}
    # types: integer count + boolean online, in the model AND its JSON dump (not diagnostic strings)
    assert isinstance(snap.activity[0].data_points, int) and snap.activity[0].online is True
    dumped = snap.model_dump()["activity"][0]
    assert dumped["data_points"] == 14 and dumped["online"] is True
    # field is data_points, NOT values (avoids Jinja resolving .values to dict.values())
    assert "values" not in dumped and "data_points" in dumped
    # selected device's per-interval data-point rate (ts1=6, ts2=8)
    assert [p.v for p in snap.activity_series] == [6.0, 8.0]


def test_snapshot_activity_off_by_default() -> None:
    fake = FakeSession()
    snap = monitoring.snapshot(fake, fake, "tid", "24h", None, None, "ok")  # type: ignore[arg-type]
    assert snap.activity == [] and snap.activity_series == []  # Monitoring path unaffected


class _CountFake:
    """A TB session stub that returns a fixed COUNT payload for values/timeseries."""

    def __init__(self, data: Any) -> None:
        self._data = data
        self.calls = 0

    def _get(self, path: str, **kw: Any) -> Any:
        if "values/timeseries" in path and kw.get("agg") == "COUNT":
            self.calls += 1
            return self._data
        return {}


def test_activity_one_key() -> None:
    f = _CountFake({"temperature": [{"ts": 1, "value": "5"}]})
    series = monitoring._activity_series(f, "d", "24h")  # type: ignore[arg-type]
    assert [p.v for p in series] == [5.0]
    assert monitoring._activity_total(series) == 5


def test_activity_multiple_keys_summed_per_bucket() -> None:
    f = _CountFake(
        {
            "temperature": [{"ts": 1, "value": "3"}, {"ts": 2, "value": "4"}],
            "humidity": [{"ts": 1, "value": "3"}, {"ts": 2, "value": "4"}],
        }
    )
    series = monitoring._activity_series(f, "d", "24h")  # type: ignore[arg-type]
    assert [(p.v) for p in series] == [6.0, 8.0]
    assert monitoring._activity_total(series) == 14


def test_activity_keys_with_different_sample_counts() -> None:
    # a key missing from a bucket contributes 0 to that bucket (only present points are summed)
    f = _CountFake(
        {
            "temperature": [
                {"ts": 1, "value": "2"},
                {"ts": 2, "value": "2"},
                {"ts": 3, "value": "2"},
            ],
            "humidity": [{"ts": 1, "value": "5"}],
        }
    )
    series = monitoring._activity_series(f, "d", "24h")  # type: ignore[arg-type]
    assert [p.v for p in series] == [7.0, 2.0, 2.0]  # ts1=2+5, ts2=2, ts3=2
    assert monitoring._activity_total(series) == 11


def test_activity_empty_and_no_keys() -> None:
    # empty device (no COUNT data) and a device with no telemetry keys both yield 0
    empty = _CountFake({})
    assert monitoring._activity_series(empty, "d", "24h") == []  # type: ignore[arg-type]
    assert monitoring._activity_total([]) == 0
    not_dict = _CountFake([])  # TB returned a non-dict → defensive empty
    assert monitoring._activity_series(not_dict, "d", "24h") == []  # type: ignore[arg-type]


def test_activity_boundary_timestamps_included() -> None:
    back, _interval, _agg = monitoring.RANGES["24h"]
    end = 1_000_000_000_000
    start = end - back * 1000
    f = _CountFake({"temperature": [{"ts": start, "value": "1"}, {"ts": end, "value": "1"}]})
    series = monitoring._activity_series(f, "d", "24h")  # type: ignore[arg-type]
    assert monitoring._activity_total(series) == 2  # both boundary points counted


def test_activity_all_ranges_run() -> None:
    for rng in monitoring.RANGES:
        f = _CountFake({"temperature": [{"ts": 1, "value": "2"}]})
        series = monitoring._activity_series(f, "d", rng)  # type: ignore[arg-type]
        assert monitoring._activity_total(series) == 2 and f.calls == 1


def test_activity_cache_separation(
    client: TestClient, flags_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Telemetry (with_activity) and ordinary monitoring/data must NOT share a cache entry, even for
    identical (project, range, device, key) — else one would serve the other's payload."""
    from contextlib import contextmanager

    from sqlalchemy.orm import Session

    from app.db import get_engine
    from app.models import Project, ProjectMember

    monitoring._CACHE.clear()
    with Session(get_engine()) as db:
        db.add_all(
            [
                Project(
                    id="pc",
                    slug="pc",
                    name="PC",
                    provisioning_state="provisioned",
                    tb_tenant_id="t",
                ),
                ProjectMember(
                    project_id="pc", user_id="cu", role="owner", tb_user_id="tb", status="active"
                ),
            ]
        )
        db.commit()

    user = SimpleNamespace(id="cu", email="c@x.io", role="student")
    monkeypatch.setattr("app.project.load_user", lambda request, db: user)
    fake = FakeSession()

    @contextmanager
    def fake_as_project(member: Any) -> Any:
        yield fake, fake

    monkeypatch.setattr("app.routers.monitoring.as_project", fake_as_project)

    # ordinary monitoring JSON first (no activity), then telemetry (with activity) — same base key
    r_mon = client.get("/projects/pc/monitoring/data")
    assert r_mon.status_code == 200 and r_mon.json()["activity"] == []
    r_tel = client.get("/projects/pc/telemetry")
    assert r_tel.status_code == 200 and "Telemetry activity" in r_tel.text and "d1" in r_tel.text
    # rendered count is the number, not Jinja resolving .values to a dict method
    assert "14" in r_tel.text and "built-in method" not in r_tel.text
    # and the reverse order still keeps them separate (monitoring stays activity-free)
    assert client.get("/projects/pc/monitoring/data").json()["activity"] == []


def test_snapshot_bad_range_clamps() -> None:
    snap = monitoring.snapshot(FakeSession(), FakeSession(), "tid", "bogus", None, None, "unknown")  # type: ignore[arg-type]
    assert snap.range == monitoring.DEFAULT_RANGE
