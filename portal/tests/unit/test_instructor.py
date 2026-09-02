from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import ClassCode, PortalUser


def _instructor(client: TestClient, db: Session, monkeypatch, role: str = "instructor"):  # noqa: ANN001, ANN202
    user = PortalUser(
        id="t-1",
        email="prof@uni.edu",
        kc_user_id="kc-t1",
        role=role,
        provisioning_state="provisioned",
    )
    db.add(user)
    db.commit()
    monkeypatch.setattr("app.routers.instructor.load_user", lambda request, db: user)
    return user


def test_console_requires_instructor_role(client: TestClient, db: Session, monkeypatch) -> None:  # noqa: ANN001
    student = PortalUser(id="s-1", email="kid@x.io", kc_user_id="kc-s1", role="student")
    db.add(student)
    db.commit()
    monkeypatch.setattr("app.routers.instructor.load_user", lambda request, db: student)
    assert client.get("/teach").status_code == 403


def test_create_and_deactivate_code(client: TestClient, db: Session, monkeypatch) -> None:  # noqa: ANN001
    _instructor(client, db, monkeypatch)
    r = client.post("/teach/codes", data={"cohort": "CS101 Fall", "max_uses": "50", "days": "90"})
    assert r.status_code == 303
    code = (
        db.scalars(db.query(ClassCode).statement).first()
        if False
        else db.scalar(db.query(ClassCode).statement.limit(1))
    )
    from sqlalchemy import select

    code = db.scalar(select(ClassCode))
    assert code and code.cohort == "cs101-fall" and code.max_uses == 50 and code.active
    r = client.get("/teach")
    assert r.status_code == 200 and code.code in r.text
    r = client.post(f"/teach/codes/{code.code}/deactivate")
    assert r.status_code == 303
    db.expire_all()
    assert db.get(ClassCode, code.code).active is False  # type: ignore[union-attr]


def test_roster_scoped_to_own_cohorts(client: TestClient, db: Session, monkeypatch) -> None:  # noqa: ANN001
    _instructor(client, db, monkeypatch)
    db.add(ClassCode(code="MINE-1", cohort="mine", instructor_email="prof@uni.edu"))
    db.add(PortalUser(id="s-2", email="a@x.io", kc_user_id="k2", cohort="mine"))
    db.commit()

    class NoTB:
        def impersonate(self, uid: str):  # noqa: ANN202
            raise RuntimeError("no tb in unit tests")

        def close(self) -> None: ...

    monkeypatch.setattr("app.routers.instructor.sysadmin_client", lambda: NoTB())
    r = client.get("/teach/cohort/mine")
    assert r.status_code == 200 and "a@x.io" in r.text
    assert client.get("/teach/cohort/other").status_code == 403


def test_suspend_flow(client: TestClient, db: Session, monkeypatch) -> None:  # noqa: ANN001
    _instructor(client, db, monkeypatch)
    db.add(ClassCode(code="MINE-2", cohort="m2", instructor_email="prof@uni.edu"))
    db.add(PortalUser(id="s-3", email="b@x.io", kc_user_id="kc-b", cohort="m2", tb_user_id="tb-b"))
    db.commit()
    kc_calls, tb_calls = [], []

    class FakeKC:
        def set_enabled(self, uid: str, enabled: bool) -> None:
            kc_calls.append((uid, enabled))

    monkeypatch.setattr("app.routers.instructor.KeycloakAdmin", FakeKC)
    monkeypatch.setattr(
        "app.routers.instructor.suspend_student",
        lambda sa, email, suspended: tb_calls.append((email, suspended)),
    )

    class NoTB:
        def close(self) -> None: ...

    monkeypatch.setattr("app.routers.instructor.sysadmin_client", lambda: NoTB())
    r = client.post("/teach/cohort/m2/suspend", data={"email": "b@x.io", "action": "suspend"})
    assert r.status_code == 303
    assert kc_calls == [("kc-b", False)] and tb_calls == [("b@x.io", True)]
    db.expire_all()
    assert db.scalar(db.query(PortalUser).statement.where(PortalUser.email == "b@x.io")) is not None
    from sqlalchemy import select

    assert db.scalar(select(PortalUser).where(PortalUser.email == "b@x.io")).role == "suspended"  # type: ignore[union-attr]
