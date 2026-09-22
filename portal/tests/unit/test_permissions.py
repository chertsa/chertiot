"""v2 Phase 4 — central authorization model: matrix unit tests + HTTP deny/allow over routes."""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import permissions
from app.config import get_settings
from app.db import get_engine
from app.models import Project, ProjectMember
from app.permissions import Cap


def _member(role: str = "member", status: str = "active") -> Any:
    return SimpleNamespace(role=role, status=status)


# ---- matrix ----
def test_project_can_owner_holds_everything() -> None:
    owner = _member("owner")
    for cap in Cap:
        if cap in (Cap.INSTRUCTOR_CONSOLE, Cap.PLATFORM_MONITORING):
            continue  # platform caps are not project caps
        assert permissions.project_can(owner, cap) is True


def test_project_can_member_denied_owner_only() -> None:
    m = _member("member")
    owner_only = {
        Cap.ALERT_ACK_CRITICAL,
        Cap.MEMBER_INVITE,
        Cap.MEMBER_MANAGE,
        Cap.JOIN_RESOLVE,
        Cap.PROJECT_DELETE,
    }
    for cap in owner_only:
        assert permissions.project_can(m, cap) is False
    # but any active member holds the shared caps
    for cap in (Cap.ALERT_ACK, Cap.ALERT_MANAGE, Cap.DEVICE_MANAGE, Cap.NOTEBOOK_LAUNCH):
        assert permissions.project_can(m, cap) is True


def test_project_can_inactive_or_missing_denied() -> None:
    assert permissions.project_can(None, Cap.ALERT_ACK) is False
    assert permissions.project_can(_member("owner", status="disabled"), Cap.ALERT_ACK) is False


def test_ack_cap_by_severity() -> None:
    assert permissions.ack_cap("CRITICAL") is Cap.ALERT_ACK_CRITICAL
    assert permissions.ack_cap("critical") is Cap.ALERT_ACK_CRITICAL
    for s in ("MAJOR", "MINOR", "WARNING", "", "anything"):
        assert permissions.ack_cap(s) is Cap.ALERT_ACK


def test_platform_can_and_is_staff() -> None:
    student = SimpleNamespace(role="student")
    instr = SimpleNamespace(role="instructor")
    admin = SimpleNamespace(role="admin")
    for cap in (Cap.PLATFORM_MONITORING, Cap.INSTRUCTOR_CONSOLE):
        assert permissions.platform_can(student, cap) is False
        assert permissions.platform_can(instr, cap) is True
        assert permissions.platform_can(admin, cap) is True
    # a project cap is never granted by platform_can; None is always denied
    assert permissions.platform_can(admin, Cap.PROJECT_DELETE) is False
    assert permissions.platform_can(None, Cap.PLATFORM_MONITORING) is False
    assert permissions.is_staff(student) is False and permissions.is_staff(instr) is True


# ---- HTTP: owner-only project actions deny a plain member ----
def _seed(role: str) -> Any:
    with Session(get_engine()) as db:
        db.add_all(
            [
                Project(
                    id="pp",
                    slug="pp",
                    name="PP",
                    provisioning_state="provisioned",
                    tb_tenant_id="t",
                ),
                ProjectMember(
                    project_id="pp", user_id="mu", role=role, tb_user_id="tb", status="active"
                ),
            ]
        )
        db.commit()
    return SimpleNamespace(id="mu", email="m@x.io", role="student")


def test_member_cannot_delete_or_invite(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.main

    client = TestClient(app.main.app, follow_redirects=False)
    user = _seed("member")
    monkeypatch.setattr("app.project.load_user", lambda request, db: user)
    assert client.post("/projects/pp/delete").status_code == 403
    assert client.post("/projects/pp/invite", data={"email": "x@y.io"}).status_code == 403


def test_ack_critical_owner_only_over_http(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.main

    s = get_settings()
    monkeypatch.setattr(s, "monitoring_enabled", True)

    class FakeAckSession:
        def _get(self, path: str, **kw: Any) -> Any:
            return {"severity": "CRITICAL"}

        def _post(self, path: str, body: Any = None, **kw: Any) -> Any:
            return {}

    @contextmanager
    def fake_as_project(member: Any) -> Any:
        yield FakeAckSession(), FakeAckSession()

    monkeypatch.setattr("app.routers.monitoring.as_project", fake_as_project)

    # member → 403 on a CRITICAL alarm
    member = _seed("member")
    monkeypatch.setattr("app.project.load_user", lambda request, db: member)
    client = TestClient(app.main.app, follow_redirects=False)
    assert client.post("/projects/pp/monitoring/alarms/a1/ack").status_code == 403

    # owner → allowed (303 back to monitoring)
    with Session(get_engine()) as db:
        db.query(ProjectMember).filter_by(project_id="pp").delete()
        db.add(
            ProjectMember(
                project_id="pp", user_id="ow", role="owner", tb_user_id="tb", status="active"
            )
        )
        db.commit()
    owner = SimpleNamespace(id="ow", email="o@x.io", role="student")
    monkeypatch.setattr("app.project.load_user", lambda request, db: owner)
    assert client.post("/projects/pp/monitoring/alarms/a1/ack").status_code == 303
