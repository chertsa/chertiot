"""v2 shell corrections: platform-Grafana role gate, per-project notebook launch (controlled),
Members/Settings page, and the notebook storage boundary."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import PortalUser, Project, ProjectMember


def _user(db: Session, role: str = "student", uid: str = "u1", email: str = "s@x.io") -> PortalUser:
    u = PortalUser(id=uid, email=email, kc_user_id="kc-" + uid, role=role)
    db.add(u)
    db.commit()
    return u


def _project(db: Session, pid: str = "p1") -> Project:
    p = Project(
        id=pid, slug=pid, name="P " + pid, provisioning_state="provisioned", tb_tenant_id="t-" + pid
    )
    db.add(p)
    db.commit()
    return p


def _member(db: Session, p: Project, u: PortalUser, role: str = "owner") -> ProjectMember:
    m = ProjectMember(
        project_id=p.id, user_id=u.id, role=role, tb_user_id="tb-" + u.id, status="active"
    )
    db.add(m)
    db.commit()
    return m


# ---- platform Grafana is instructor/admin-only, enforced at the launch route (not just hidden) --
def test_grafana_launch_forbidden_for_student(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    u = _user(db, role="student")
    monkeypatch.setattr("app.routers.home.load_user", lambda request, db: u)
    r = client.get("/grafana")
    assert r.status_code == 403 and "staff-only" in r.text.lower()


def test_grafana_launch_redirects_for_instructor(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    u = _user(db, role="instructor", uid="i1", email="prof@x.io")
    monkeypatch.setattr("app.routers.home.load_user", lambda request, db: u)
    r = client.get("/grafana", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("https://grafana.")


# ---- per-project notebook launch: membership-gated, controlled degraded state, no raw hub 400 ----
def test_notebooks_non_member_redirected_home(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    u = _user(db)
    _project(db)  # user is NOT a member
    monkeypatch.setattr("app.project.load_user", lambda request, db: u)
    r = client.get("/projects/p1/notebooks", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/home"


def test_notebooks_lab_disabled_is_controlled_page(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    u = _user(db)
    p = _project(db)
    _member(db, p, u)
    monkeypatch.setattr("app.project.load_user", lambda request, db: u)
    monkeypatch.setattr("app.lab.enabled", lambda: False)
    r = client.get("/projects/p1/notebooks")
    # controlled portal page (503), never a raw JupyterHub error
    assert r.status_code == 503 and "temporarily unavailable" in r.text.lower()
    assert "400" not in r.text and "Named servers" not in r.text


def test_notebooks_launch_redirects_to_named_server(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    u = _user(db, email="owner@x.io")
    p = _project(db)
    _member(db, p, u)
    monkeypatch.setattr("app.project.load_user", lambda request, db: u)
    monkeypatch.setattr("app.lab.enabled", lambda: True)
    monkeypatch.setattr("app.lab.healthy", lambda timeout=3.0: True)
    r = client.get("/projects/p1/notebooks", follow_redirects=False)
    assert r.status_code == 303
    loc = r.headers["location"]
    # server name is the immutable project id; user is url-encoded
    assert loc.endswith("/hub/spawn/owner%40x.io/p1") and "lab." in loc


# ---- Members/Settings holds the moved controls; Overview no longer does ----
def test_settings_page_has_moved_controls_for_owner(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    u = _user(db, email="owner@x.io")
    p = _project(db)
    _member(db, p, u)
    monkeypatch.setattr("app.project.load_user", lambda request, db: u)
    r = client.get("/projects/p1/settings")
    assert r.status_code == 200
    for token in ("Invite a member", "Reset starter dashboard", "Delete project", "Danger zone"):
        assert token in r.text


def test_overview_defers_admin_to_settings(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    u = _user(db, email="owner@x.io")
    p = _project(db)
    _member(db, p, u)
    # workspace() calls load_user directly (not require_membership)
    monkeypatch.setattr("app.routers.projects.load_user", lambda request, db: u)
    r = client.get("/projects/p1")
    assert r.status_code == 200
    # destructive admin lives in Settings now, not on the operational Overview
    assert 'action="/projects/p1/delete"' not in r.text
    assert 'action="/projects/p1/invite"' not in r.text
    assert "/projects/p1/settings" in r.text  # a pointer to Settings remains


# ---- storage boundary + launch URL are per (user, project) ----
def test_notebook_storage_boundary_is_per_user_and_project() -> None:
    from pathlib import Path

    cfg = (Path(__file__).resolve().parents[3] / "lab/hub/jupyterhub_config.py").read_text()
    vol = 'c.DockerSpawner.volumes = {"jupyter-{username}-{servername}": "/home/jovyan/work"}'
    assert vol in cfg
    assert "c.JupyterHub.named_server_limit_per_user" in cfg
    from app import lab

    a = lab.spawn_url("alice@x.io", "proj-A")
    b = lab.spawn_url("alice@x.io", "proj-B")
    c = lab.spawn_url("bob@x.io", "proj-A")
    # different project or user ⇒ different named server ⇒ different volume
    assert a != b and a != c


def test_delete_project_notebooks_calls_hub_admin_api(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import lab

    calls: list[tuple[str, str, dict[str, Any]]] = []

    class FakeResp:
        status_code = 204

    def fake_request(method: str, url: str, **kw: Any) -> FakeResp:
        calls.append((method, url, kw))
        return FakeResp()

    monkeypatch.setattr("app.lab.httpx.request", fake_request)
    monkeypatch.setattr(
        "app.lab.get_settings",
        lambda: type(
            "S",
            (),
            {"lab_internal_secret": "tok", "lab_internal_url": "http://jupyterhub:8000"},
        )(),
    )
    lab.delete_project_notebooks("p1", ["a@x.io", "b@x.io"])
    assert len(calls) == 2
    m, url, kw = calls[0]
    assert m == "DELETE" and url.endswith("/hub/api/users/a%40x.io/servers/p1")
    assert kw["headers"]["Authorization"] == "token tok"
