from fastapi.testclient import TestClient

from app.ratelimit import SlidingWindow, limiter
from tests.unit.conftest import FakeKeycloak

GOOD = {
    "email": "x@example.com",
    "password": "correct-horse-battery",
    "password_confirm": "correct-horse-battery",
    "age_attested": "yes",
}


def test_sliding_window() -> None:
    w = SlidingWindow()
    assert all(w.allow("k", 3, 10, now=t) for t in (0, 1, 2))
    assert not w.allow("k", 3, 10, now=3)
    assert w.allow("k", 3, 10, now=10.5)  # first hit expired


def test_signup_is_rate_limited_per_ip(client: TestClient, kc: FakeKeycloak) -> None:
    limiter.reset()
    codes = [
        client.post("/signup", data={**GOOD, "email": f"u{i}@example.com"}).status_code
        for i in range(6)
    ]
    assert codes[:5] == [303] * 5 and codes[5] == 429
    limiter.reset()
