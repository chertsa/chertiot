"""Lock the Grafana staff-only OAuth gating config so a regression fails CI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_compose_grafana_oauth_is_strict_role_gated() -> None:
    compose = (ROOT / "docker-compose.yml").read_text()
    assert 'GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_STRICT: "true"' in compose
    # role path maps staff and denies everyone else via an EMPTY fallback (never the 'None' role)
    assert "contains(roles[*], 'platform-admin') && 'Admin'" in compose
    assert "contains(roles[*], 'platform-instructor') && 'Viewer'" in compose
    assert "|| ''\"" in compose  # empty fallback -> strict denies
    assert "|| 'None'" not in compose  # 'None' would be a valid no-access role (does NOT deny)


def test_keycloak_grafana_client_emits_roles_claim() -> None:
    setup = (ROOT / "portal/scripts/setup_keycloak.py").read_text()
    assert "oidc-usermodel-realm-role-mapper" in setup
    assert '"claim.name": "roles"' in setup
    assert '"userinfo.token.claim": "true"' in setup  # Grafana reads roles from userinfo
