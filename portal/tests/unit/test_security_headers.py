"""v2 Phase 0: the security-headers/CSP middleware sets a self-only CSP on every response."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_csp_and_security_headers_present(client: TestClient) -> None:
    r = client.get("/healthz")
    csp = r.headers.get("content-security-policy", "")
    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "base-uri 'self'" in csp
    assert "frame-ancestors 'self'" in csp
    # zero external runtime assets: no external origin is ever allow-listed in the policy
    assert "http://" not in csp and "https://" not in csp and "//" not in csp
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("referrer-policy") == "same-origin"


def test_features_flag_default_off() -> None:
    from app.features import flags

    assert flags()["monitoring"] is False  # ships dark until enabled staging-first
