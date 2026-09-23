"""Durable cross-project negative matrix: a signed-in user who is NOT a member of a project is
denied on every project capability route (page routes → 303 redirect away; API/mutation → 403).
Device/alarm-UUID substitution and true tenant-data isolation are additionally exercised on staging;
here we lock the route-level authorization so a regression fails CI."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_engine
from app.models import Project, ProjectMember

# (method, path, expected status for a non-member, form data). 303 = redirected away (page);
# 403 = api/mutation. Form data is sent where the route requires it, so validation (422) never
# pre-empts the authorization check.
CASES: list[tuple[str, str, int, dict[str, str]]] = [
    ("get", "/projects/P/devices", 303, {}),
    ("get", "/projects/P/devices/dev-x", 303, {}),
    ("post", "/projects/P/devices", 303, {"name": "d"}),
    ("post", "/projects/P/devices/dev-x/rename", 303, {"name": "d"}),
    ("post", "/projects/P/devices/dev-x/revoke", 303, {}),
    ("post", "/projects/P/devices/dev-x/delete", 303, {}),
    ("get", "/projects/P/telemetry", 303, {}),
    ("get", "/projects/P/monitoring", 303, {}),
    ("get", "/projects/P/monitoring/data", 403, {}),
    ("post", "/projects/P/monitoring/alarms/al-x/ack", 403, {}),
    ("get", "/projects/P/alerts", 303, {}),
    (
        "post",
        "/projects/P/alerts",
        303,
        {"device_name": "d", "key": "temperature", "op": ">", "threshold": "1"},
    ),
    ("post", "/projects/P/alerts/rule-x/delete", 303, {}),
    ("get", "/projects/P/lora", 303, {}),
    ("post", "/projects/P/lora", 303, {}),
    ("get", "/projects/P/report", 303, {}),
    ("get", "/projects/P/thingsboard", 303, {}),
    ("get", "/projects/P/notebooks", 303, {}),
    ("get", "/projects/P/flows", 303, {}),
    ("post", "/projects/P/flows/start", 303, {}),
    ("post", "/projects/P/flows/stop", 303, {}),
    ("get", "/projects/P/settings", 303, {}),
    ("post", "/projects/P/dashboard/reset", 303, {}),
    ("post", "/projects/P/delete", 303, {}),
    ("post", "/projects/P/invite", 303, {"email": "x@y.io"}),
    ("post", "/projects/P/members/m-x/remove", 303, {}),
    ("post", "/projects/P/requests/r-x/approve", 303, {}),
]


@pytest.fixture
def other_owned_project() -> str:
    """A provisioned project owned by SOMEONE ELSE; the test actor is not a member."""
    with Session(get_engine()) as db:
        db.add_all(
            [
                Project(
                    id="P", slug="p", name="P", provisioning_state="provisioned", tb_tenant_id="t"
                ),
                ProjectMember(
                    project_id="P",
                    user_id="owner-else",
                    role="owner",
                    tb_user_id="tb",
                    status="active",
                ),
            ]
        )
        db.commit()
    return "P"


@pytest.mark.parametrize(("method", "path", "expected", "data"), CASES)
def test_non_member_denied_on_every_route(
    client: TestClient,
    other_owned_project: str,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    expected: int,
    data: dict[str, str],
) -> None:
    s = get_settings()
    monkeypatch.setattr(s, "monitoring_enabled", True)
    monkeypatch.setattr(s, "telemetry_enabled", True)
    outsider = SimpleNamespace(id="outsider", email="out@x.io", role="student")
    monkeypatch.setattr("app.project.load_user", lambda request, db: outsider)
    resp: Any = client.request(method, path, data=data or None, follow_redirects=False)
    assert resp.status_code == expected, f"{method} {path} -> {resp.status_code} (want {expected})"
    if expected == 303:  # redirected away from the project, never into it
        assert resp.headers["location"] in ("/home", "/login")


def test_flows_auth_denies_non_member(
    client: TestClient, other_owned_project: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    outsider = SimpleNamespace(id="outsider", email="out@x.io", role="student")
    monkeypatch.setattr("app.routers.flows.load_user", lambda request, db: outsider)
    # Caddy forward-auth for another project's editor path → 403
    r = client.get("/flows/auth", headers={"x-flows-uid": "P"})
    assert r.status_code == 403
