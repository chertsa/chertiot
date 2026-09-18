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


def test_projects_roster(client: TestClient, db: Session, monkeypatch) -> None:  # noqa: ANN001
    from app.models import Project, ProjectMember

    _instructor(client, db, monkeypatch)
    db.add_all(
        [
            PortalUser(id="s-2", email="a@x.io", kc_user_id="k2"),
            Project(
                id="pr1",
                slug="alpha",
                name="Alpha",
                provisioning_state="provisioned",
                tb_tenant_id="t1",
            ),
            ProjectMember(
                project_id="pr1", user_id="s-2", role="owner", tb_user_id="tb-a", status="active"
            ),
        ]
    )
    db.commit()

    class NoTB:
        def impersonate(self, uid: str):  # noqa: ANN202
            raise RuntimeError("no tb in unit tests")

        def close(self) -> None: ...

    monkeypatch.setattr("app.routers.instructor.sysadmin_client", lambda: NoTB())
    r = client.get("/teach/projects")
    # roster lists the project + its owner; device count degrades to "—" without TB
    assert r.status_code == 200 and "Alpha" in r.text and "a@x.io" in r.text


def test_projects_roster_requires_instructor(client: TestClient, db: Session, monkeypatch) -> None:  # noqa: ANN001
    student = PortalUser(id="s-9", email="kid2@x.io", kc_user_id="kc-s9", role="student")
    db.add(student)
    db.commit()
    monkeypatch.setattr("app.routers.instructor.load_user", lambda request, db: student)
    assert client.get("/teach/projects").status_code == 403
