from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import PortalUser, Project, ProjectMember


def test_lab_token_scoped_to_project_membership(
    client: TestClient, db: Session, monkeypatch
) -> None:  # noqa: ANN001, E501
    monkeypatch.setenv("LAB_INTERNAL_SECRET", "s3cret")
    from app.config import get_settings

    get_settings.cache_clear()
    db.add_all(
        [
            PortalUser(id="u1", email="a@x.io", kc_user_id="k1"),
            Project(
                id="p1", slug="p1", name="P1", provisioning_state="provisioned", tb_tenant_id="t1"
            ),
            ProjectMember(
                project_id="p1", user_id="u1", role="owner", tb_user_id="tb1", status="active"
            ),
        ]
    )
    db.commit()
    body = {"email": "a@x.io", "project_id": "p1"}

    # secret gate
    assert client.post("/internal/lab-token", json=body).status_code == 403
    assert (
        client.post("/internal/lab-token", json=body, headers={"X-Lab-Secret": "wrong"}).status_code
        == 403
    )

    class FakeSession:
        class _T:
            token = "tb-jwt-abc"  # noqa: S105 - fake JWT for the stub

        _tokens = _T()

        def close(self) -> None: ...

    class FakeSysadmin:
        def impersonate(self, uid: str) -> FakeSession:
            assert uid == "tb1"
            return FakeSession()

        def close(self) -> None: ...

    monkeypatch.setattr("app.routers.internal.sysadmin_client", lambda: FakeSysadmin())
    ok = client.post("/internal/lab-token", json=body, headers={"X-Lab-Secret": "s3cret"})
    assert ok.status_code == 200 and ok.json()["token"] == "tb-jwt-abc"

    # unknown user → 404; non-member project → 403
    assert (
        client.post(
            "/internal/lab-token",
            json={"email": "nobody@x.io", "project_id": "p1"},
            headers={"X-Lab-Secret": "s3cret"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/internal/lab-token",
            json={"email": "a@x.io", "project_id": "other"},
            headers={"X-Lab-Secret": "s3cret"},
        ).status_code
        == 403
    )
    get_settings.cache_clear()
