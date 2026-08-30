"""M0.3 acceptance: Keycloak login lands the user in ThingsBoard as TENANT_ADMIN of their own
tenant (D4)."""

import os
import re
from urllib.parse import parse_qs, urlparse

from tests.e2e.conftest import make_client


def test_keycloak_login_creates_own_tenant(tb_url: str, kc_url: str) -> None:
    email = os.environ["DEV_TEST_USER_EMAIL"]
    password = os.environ["DEV_TEST_USER_PASSWORD"]

    with make_client(follow_redirects=False) as s:
        # 1. TB advertises the Keycloak client for this domain.
        r = s.post(f"{tb_url}/api/noauth/oauth2Clients", params={"platform": "WEB"})
        assert r.status_code == 200, r.text
        clients = r.json()
        assert clients, "no OAuth2 clients advertised for this domain — run `make bootstrap`"
        login_path = clients[0]["url"]

        # 2. Follow TB → Keycloak authorization redirect.
        r = s.get(f"{tb_url}{login_path}")
        assert r.status_code in (302, 303), r.text
        kc_auth = r.headers["location"]
        assert kc_auth.startswith(kc_url), kc_auth
        r = s.get(kc_auth)
        assert r.status_code == 200
        form_action = re.search(r'action="([^"]+)"', r.text)
        assert form_action, "Keycloak login form not found"

        # 3. Submit credentials to Keycloak; it redirects back to TB's code endpoint.
        action = form_action.group(1).replace("&amp;", "&")
        r = s.post(action, data={"username": email, "password": password})
        assert r.status_code in (302, 303), r.text[:500]
        back = r.headers["location"]
        assert back.startswith(f"{tb_url}/login/oauth2/code/"), back

        # 4. TB exchanges the code (backchannel to Keycloak) and redirects with tokens.
        r = s.get(back)
        assert r.status_code in (302, 303), r.text[:500]
        final = r.headers["location"]
        qs = parse_qs(urlparse(final).query)
        assert "accessToken" in qs, f"TB did not issue a token: {final}"
        token = qs["accessToken"][0]

    # 5. The user is TENANT_ADMIN of a tenant named after their email.
    auth = {"X-Authorization": f"Bearer {token}"}
    api = make_client()
    me = api.get(f"{tb_url}/api/auth/user", headers=auth)
    assert me.status_code == 200, me.text
    user = me.json()
    assert user["email"] == email
    assert user["authority"] == "TENANT_ADMIN"
    tenant = api.get(
        f"{tb_url}/api/tenant/{user['tenantId']['id']}", headers=auth, timeout=30
    ).json()
    assert tenant["title"] == email
