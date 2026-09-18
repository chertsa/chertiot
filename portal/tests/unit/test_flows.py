from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import flows
from app.models import FlowInstance, PortalUser, Project, ProjectMember


def _member(db: Session, uid: str = "u-1", pid: str = "p-1") -> tuple[PortalUser, Project]:
    """A signed-in user who is an active member of project `pid`."""
    user = PortalUser(id=uid, email=f"{uid}@example.com", kc_user_id=f"kc-{uid}")
    project = Project(
        id=pid, slug=pid, name="Proj", provisioning_state="provisioned", tb_tenant_id="t"
    )
    db.add_all(
        [
            user,
            project,
            ProjectMember(
                project_id=pid, user_id=uid, role="owner", tb_user_id="tbu", status="active"
            ),
        ]
    )
    db.commit()
    return user, project


def test_forward_auth_requires_session(client: TestClient, db: Session) -> None:
    _member(db)
    # no session cookie / no user → 401
    r = client.get("/flows/auth", headers={"x-forwarded-uri": "/u/p-1/"})
    assert r.status_code == 401


def test_forward_auth_scopes_paths_to_project(client: TestClient, db: Session, monkeypatch) -> None:  # noqa: ANN001
    user, project = _member(db, "u-owner", "p-owner")
    monkeypatch.setattr("app.routers.flows.load_user", lambda request, db: user)
    ok = client.get("/flows/auth", headers={"x-forwarded-uri": f"/u/{project.id}/red/main.js"})
    assert ok.status_code == 200 and ok.headers["X-Flows-User"] == user.id
    other = client.get("/flows/auth", headers={"x-forwarded-uri": "/u/someone-else/"})
    assert other.status_code == 403
    missing = client.get("/flows/auth")
    assert missing.status_code == 403


def test_forward_auth_touches_last_active(client: TestClient, db: Session, monkeypatch) -> None:  # noqa: ANN001
    user, project = _member(db, "u-act", "p-act")
    monkeypatch.setattr("app.routers.flows.load_user", lambda request, db: user)
    old = datetime.now(UTC) - timedelta(hours=2)
    db.add(
        FlowInstance(
            project_id=project.id, container_name="nodered-p-act", state="running", last_active=old
        )
    )
    db.commit()
    client.get("/flows/auth", headers={"x-forwarded-uri": f"/u/{project.id}/"})
    db.expire_all()
    assert db.get(FlowInstance, project.id).last_active.replace(tzinfo=UTC) > old  # type: ignore[union-attr]


def test_cull_idle_stops_only_stale(monkeypatch, db: Session) -> None:  # noqa: ANN001
    stopped: list[str] = []
    monkeypatch.setattr(flows, "stop", lambda pid: stopped.append(pid) or True)
    now = datetime.now(UTC)
    db.add(
        FlowInstance(
            project_id="stale",
            container_name="nodered-stale",
            state="running",
            last_active=now - timedelta(hours=1),
        )
    )
    db.add(
        FlowInstance(
            project_id="fresh", container_name="nodered-fresh", state="running", last_active=now
        )
    )
    db.commit()
    from app.db import session_factory

    n = flows.cull_idle(session_factory())
    assert n == 1 and stopped == ["stale"]
    db.expire_all()
    assert db.get(FlowInstance, "stale").state == "stopped"  # type: ignore[union-attr]
    assert db.get(FlowInstance, "fresh").state == "running"  # type: ignore[union-attr]
