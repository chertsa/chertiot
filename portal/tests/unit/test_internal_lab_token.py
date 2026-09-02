from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import PortalUser


def test_lab_token_requires_secret(client: TestClient, db: Session, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("LAB_INTERNAL_SECRET", "s3cret")
    from app.config import get_settings

    get_settings.cache_clear()
    db.add(
        PortalUser(
            id="u1",
            email="a@x.io",
            kc_user_id="k1",
            provisioning_state="provisioned",
            tb_user_id="tb1",
        )
    )
    db.commit()

    r = client.post("/internal/lab-token", json={"email": "a@x.io"})
    assert r.status_code == 403
    r = client.post(
        "/internal/lab-token", json={"email": "a@x.io"}, headers={"X-Lab-Secret": "wrong"}
    )
    assert r.status_code == 403

    class FakeStudent:
        class _T:
            token = "tb-jwt-abc"  # noqa: S105 - fake JWT for the stub

        _tokens = _T()

        def close(self) -> None: ...

    class FakeSysadmin:
        def impersonate(self, uid: str) -> FakeStudent:
            assert uid == "tb1"
            return FakeStudent()

        def close(self) -> None: ...

    monkeypatch.setattr("app.routers.internal.sysadmin_client", lambda: FakeSysadmin())
    r = client.post(
        "/internal/lab-token", json={"email": "a@x.io"}, headers={"X-Lab-Secret": "s3cret"}
    )
    assert r.status_code == 200 and r.json()["token"] == "tb-jwt-abc"
    r = client.post(
        "/internal/lab-token", json={"email": "nobody@x.io"}, headers={"X-Lab-Secret": "s3cret"}
    )
    assert r.status_code == 404
    get_settings.cache_clear()
