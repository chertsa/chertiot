#!/usr/bin/env python3
"""Idempotent Keycloak configuration for the CHERT login theme (standard library only).

Sets, on an existing realm (or creates it with --create-realm):
  - loginTheme = chert
  - internationalization ON, supported locales en + ar, default en
  - "Forgot password" ON (resetPasswordAllowed), so the reset link exists; "Remember me" ON
  - with --email-as-username: email is the username (form shows "Email", like the reference)
and, for your app's OIDC client (must exist unless --create-client):
  - Base URL = your app home (the language pill links to <Base URL><langSwitchPath>)

Safe to re-run; never touches users, credentials or other settings.

Usage:
  KC_ADMIN_PASSWORD=... python3 tools/keycloak_setup.py --kc https://auth.example.com \
      --realm myrealm --client portal --base-url https://example.com/ [--admin-user admin]
      [--create-realm] [--create-client --redirect https://example.com/auth/callback]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request


def call(method: str, url: str, token: str | None = None, body: dict | None = None,
         form: dict | None = None) -> tuple[int, dict | list | None]:
    headers = {}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"error": raw.decode(errors="replace")[:300]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kc", required=True)
    ap.add_argument("--realm", required=True)
    ap.add_argument("--client", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--admin-user", default=os.environ.get("KC_ADMIN_USER", "admin"))
    ap.add_argument("--create-realm", action="store_true")
    ap.add_argument("--create-client", action="store_true")
    ap.add_argument("--redirect")
    ap.add_argument("--email-as-username", action="store_true",
                    help="match the reference sign-in form (Email field). Only for realms where users sign in by email.")
    a = ap.parse_args()
    pw = os.environ.get("KC_ADMIN_PASSWORD")
    if not pw:
        sys.exit("set KC_ADMIN_PASSWORD (never pass secrets as arguments)")
    kc = a.kc.rstrip("/")

    st, tok = call("POST", f"{kc}/realms/master/protocol/openid-connect/token",
                   form={"grant_type": "password", "client_id": "admin-cli", "username": a.admin_user, "password": pw})
    if st != 200:
        sys.exit(f"admin login failed ({st})")
    t = tok["access_token"]  # type: ignore[index]
    admin = f"{kc}/admin/realms"

    st, realm = call("GET", f"{admin}/{a.realm}", t)
    if st == 404:
        if not a.create_realm:
            sys.exit(f"realm {a.realm} not found (use --create-realm)")
        st, _ = call("POST", admin, t, {"realm": a.realm, "enabled": True})
        print(f"realm {a.realm}: created ({st})")
        st, realm = call("GET", f"{admin}/{a.realm}", t)

    want = {"loginTheme": "chert", "internationalizationEnabled": True, "supportedLocales": ["en", "ar"],
            "defaultLocale": "en", "resetPasswordAllowed": True, "rememberMe": True}
    if a.email_as_username:  # reference look: an "Email" field instead of "Username or email"
        want.update({"registrationEmailAsUsername": True, "loginWithEmailAllowed": True, "duplicateEmailsAllowed": False})
    def same(k: str, v: object) -> bool:  # Keycloak returns supportedLocales sorted: compare as a set
        got = realm.get(k)  # type: ignore[union-attr]
        return set(got or []) == set(v) if isinstance(v, list) else got == v

    if not all(same(k, v) for k, v in want.items()):
        st, _ = call("PUT", f"{admin}/{a.realm}", t, {**realm, **want})  # type: ignore[dict-item]
        print(f"realm {a.realm}: login theme / i18n / forgot-password set ({st})")
    else:
        print(f"realm {a.realm}: already configured")

    st, clients = call("GET", f"{admin}/{a.realm}/clients?clientId={urllib.parse.quote(a.client)}", t)
    if not clients:
        if not a.create_client:
            sys.exit(f"client {a.client} not found (use --create-client --redirect ...)")
        rep = {"clientId": a.client, "protocol": "openid-connect", "publicClient": False, "standardFlowEnabled": True,
               "redirectUris": [a.redirect or a.base_url.rstrip("/") + "/*"], "webOrigins": ["+"], "baseUrl": a.base_url}
        st, _ = call("POST", f"{admin}/{a.realm}/clients", t, rep)
        print(f"client {a.client}: created ({st})")
        return
    c = clients[0]  # type: ignore[index]
    if c.get("baseUrl") != a.base_url:
        c["baseUrl"] = a.base_url
        st, _ = call("PUT", f"{admin}/{a.realm}/clients/{c['id']}", t, c)
        print(f"client {a.client}: Base URL -> {a.base_url} ({st})")
    else:
        print(f"client {a.client}: Base URL already {a.base_url}")


if __name__ == "__main__":
    main()
