from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, ClassCode, PortalUser
from tests.unit.conftest import FakeKeycloak

GOOD = {
    "email": "Ada@Example.com",
    "password": "correct-horse-battery",
    "password_confirm": "correct-horse-battery",
    "age_attested": "yes",
    "first_name": "Ada",
}


def test_signup_form_renders(client: TestClient) -> None:
    r = client.get("/signup")
    assert r.status_code == 200
    assert 'name="age_attested"' in r.text and 'name="class_code"' in r.text


def test_signup_creates_pending_user_and_sends_verification(
    client: TestClient, kc: FakeKeycloak, db: Session
) -> None:
    r = client.post("/signup", data=GOOD)
    assert r.status_code == 303 and r.headers["location"].startswith("/signup/check-email")
    user = db.scalar(select(PortalUser).where(PortalUser.email == "ada@example.com"))
    assert user and user.provisioning_state == "pending" and user.kc_user_id == "kc-1"
    assert user.cohort == "community" and user.age_attested_at is not None
    assert kc.created == [("ada@example.com", "Ada")]
    assert kc.verify_sent == [("kc-1", "http://localhost/auth/verified")]
    assert db.scalar(select(AuditLog).where(AuditLog.action == "signup"))


def test_validation_errors(client: TestClient, kc: FakeKeycloak) -> None:
    r = client.post(
        "/signup", data={**GOOD, "email": "nope", "password_confirm": "x", "age_attested": ""}
    )
    assert r.status_code == 422
    for msg in ("valid email", "don&#39;t match", "18 or older"):
        assert msg in r.text
    assert kc.created == []


def test_duplicate_email_rejected(client: TestClient, kc: FakeKeycloak) -> None:
    assert client.post("/signup", data=GOOD).status_code == 303
    r = client.post("/signup", data=GOOD)
    assert r.status_code == 422 and "Sign in instead" in r.text
    assert len(kc.created) == 1


def test_existing_keycloak_account_rejected(client: TestClient, kc: FakeKeycloak) -> None:
    kc.existing.add("ada@example.com")
    r = client.post("/signup", data=GOOD)
    assert r.status_code == 422 and "Sign in instead" in r.text


def test_class_code_routes_cohort_and_counts_uses(client: TestClient, db: Session) -> None:
    db.add(
        ClassCode(code="CS101", cohort="cs101-fall26", instructor_email="prof@uni.edu", max_uses=2)
    )
    db.add(
        ClassCode(
            code="OLD",
            cohort="x",
            instructor_email="p@u.edu",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
    )
    db.commit()
    r = client.post("/signup", data={**GOOD, "class_code": "cs101"})
    assert r.status_code == 303
    db.expire_all()
    user = db.scalar(select(PortalUser).where(PortalUser.email == "ada@example.com"))
    assert user and user.cohort == "cs101-fall26" and user.class_code == "CS101"
    assert db.get(ClassCode, "CS101").uses == 1  # type: ignore[union-attr]

    r = client.post("/signup", data={**GOOD, "email": "b@example.com", "class_code": "OLD"})
    assert r.status_code == 422 and "class code" in r.text.lower()
    r = client.post("/signup", data={**GOOD, "email": "c@example.com", "class_code": "NOPE"})
    assert r.status_code == 422


def test_home_requires_login(client: TestClient) -> None:
    r = client.get("/home")
    assert r.status_code == 303 and r.headers["location"] == "/login"
