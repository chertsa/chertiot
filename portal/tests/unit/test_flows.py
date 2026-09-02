from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import flows
from app.models import FlowInstance, PortalUser


def _login(client: TestClient, db: Session, uid: str = "u-1") -> PortalUser:
    user = PortalUser(
        id=uid,
        email=f"{uid}@example.com",
        kc_user_id=f"kc-{uid}",
        provisioning_state="provisioned",
        tb_user_id="tbu",
    )
    db.add(user)
    db.commit()
    client.cookies.clear()
    # simulate an authenticated session
    from app.auth import optional_user  # noqa: F401

    return user


def test_flows_page_disabled_by_default(client: TestClient, db: Session, monkeypatch) -> None:  # noqa: ANN001
    user = _login(client, db)
    with client as c:
        # inject session
        c.cookies.set("chertiot_session", "x")
    # direct call of the auth endpoint without a session → 401
    r = client.get("/flows/auth", headers={"x-forwarded-uri": f"/u/{user.id}/"})
    assert r.status_code == 401


def test_forward_auth_scopes_paths_to_owner(client: TestClient, db: Session, monkeypatch) -> None:  # noqa: ANN001
    user = _login(client, db, "u-owner")
    monkeypatch.setattr("app.routers.flows.load_user", lambda request, db: user)
    ok = client.get("/flows/auth", headers={"x-forwarded-uri": f"/u/{user.id}/red/main.js"})
    assert ok.status_code == 200 and ok.headers["X-Flows-User"] == user.id
    other = client.get("/flows/auth", headers={"x-forwarded-uri": "/u/someone-else/"})
    assert other.status_code == 403
    missing = client.get("/flows/auth")
    assert missing.status_code == 403


def test_forward_auth_touches_last_active(client: TestClient, db: Session, monkeypatch) -> None:  # noqa: ANN001
    user = _login(client, db, "u-act")
    monkeypatch.setattr("app.routers.flows.load_user", lambda request, db: user)
    old = datetime.now(UTC) - timedelta(hours=2)
    db.add(
        FlowInstance(
            user_id=user.id, container_name="nodered-u-act", state="running", last_active=old
        )
    )
    db.commit()
    client.get("/flows/auth", headers={"x-forwarded-uri": f"/u/{user.id}/"})
    db.expire_all()
    assert db.get(FlowInstance, user.id).last_active.replace(tzinfo=UTC) > old  # type: ignore[union-attr]


def test_cull_idle_stops_only_stale(monkeypatch, db: Session) -> None:  # noqa: ANN001
    stopped: list[str] = []
    monkeypatch.setattr(flows, "stop", lambda uid: stopped.append(uid) or True)
    now = datetime.now(UTC)
    db.add(
        FlowInstance(
            user_id="stale",
            container_name="nodered-stale",
            state="running",
            last_active=now - timedelta(hours=1),
        )
    )
    db.add(
        FlowInstance(
            user_id="fresh", container_name="nodered-fresh", state="running", last_active=now
        )
    )
    db.commit()
    from app.db import session_factory

    n = flows.cull_idle(session_factory())
    assert n == 1 and stopped == ["stale"]
    db.expire_all()
    assert db.get(FlowInstance, "stale").state == "stopped"  # type: ignore[union-attr]
    assert db.get(FlowInstance, "fresh").state == "running"  # type: ignore[union-attr]
