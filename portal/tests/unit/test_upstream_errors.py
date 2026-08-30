import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.routers.signup import get_kc

GOOD = {
    "email": "x@example.com",
    "password": "correct-horse-battery",
    "password_confirm": "correct-horse-battery",
    "age_attested": "yes",
}


class TimingOutKeycloak:
    def create_user(self, *a: object, **k: object) -> str:
        raise httpx.ReadTimeout("timed out")


def test_upstream_timeout_is_a_503_not_a_500() -> None:
    app.dependency_overrides[get_kc] = lambda: TimingOutKeycloak()
    try:
        r = TestClient(app, raise_server_exceptions=False).post("/signup", data=GOOD)
    finally:
        app.dependency_overrides.pop(get_kc, None)
    assert r.status_code == 503 and "try again" in r.text
