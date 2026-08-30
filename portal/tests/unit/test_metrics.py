from fastapi.testclient import TestClient

from app.main import app


def test_metrics_exposed() -> None:
    r = TestClient(app).get("/metrics")
    assert r.status_code == 200
    assert b"http_request" in r.content or b"python_info" in r.content
