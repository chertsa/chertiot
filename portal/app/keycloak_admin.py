"""Keycloak admin API client for the portal's service account (manage-users only, D3)."""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.config import Settings, get_settings


class KeycloakError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"keycloak {status}: {message}")
        self.status = status
        self.message = message


class KeycloakUserExistsError(KeycloakError):
    pass


class KeycloakAdmin:
    def __init__(
        self, settings: Settings | None = None, transport: httpx.BaseTransport | None = None
    ):
        s = settings or get_settings()
        self.internal = s.kc_internal_url.rstrip("/")
        self.realm = s.kc_realm
        self.client_id = "portal"
        self.client_secret = s.kc_secret_portal
        self._http = httpx.Client(timeout=20, transport=transport)
        self._token: str | None = None
        self._exp = 0.0

    def _bearer(self) -> dict[str, str]:
        if self._token is None or time.time() > self._exp - 30:
            r = self._http.post(
                f"{self.internal}/realms/{self.realm}/protocol/openid-connect/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            if r.status_code != 200:
                raise KeycloakError(r.status_code, r.text[:300])
            body = r.json()
            self._token, self._exp = body["access_token"], time.time() + int(body["expires_in"])
        return {"Authorization": f"Bearer {self._token}"}

    def _req(self, method: str, path: str, **kw: Any) -> httpx.Response:
        r = self._http.request(
            method, f"{self.internal}/admin/realms/{self.realm}{path}", headers=self._bearer(), **kw
        )
        if r.status_code == 409:
            raise KeycloakUserExistsError(409, "account already exists")
        if r.status_code >= 400:
            try:
                msg = r.json().get("errorMessage") or r.json().get("error") or r.text
            except ValueError:
                msg = r.text
            raise KeycloakError(r.status_code, str(msg)[:300])
        return r

    def create_user(
        self, email: str, password: str, first_name: str = "", last_name: str = ""
    ) -> str:
        """Creates an enabled, *unverified* user. Returns the Keycloak user id."""
        rep = {
            "username": email,
            "email": email,
            "emailVerified": False,
            "enabled": True,
            "firstName": first_name,
            "lastName": last_name,
            "requiredActions": ["VERIFY_EMAIL"],
            "credentials": [{"type": "password", "value": password, "temporary": False}],
        }
        r = self._req("POST", "/users", json=rep)
        return str(r.headers["Location"].rstrip("/").rsplit("/", 1)[-1])

    def send_verify_email(self, user_id: str, redirect_uri: str) -> None:
        self._req(
            "PUT",
            f"/users/{user_id}/send-verify-email",
            params={"client_id": self.client_id, "redirect_uri": redirect_uri},
        )

    def get_user(self, user_id: str) -> dict[str, Any]:
        return dict(self._req("GET", f"/users/{user_id}").json())

    def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        users = self._req("GET", "/users", params={"email": email, "exact": "true"}).json()
        return dict(users[0]) if users else None

    def set_enabled(self, user_id: str, enabled: bool) -> None:
        self._req("PUT", f"/users/{user_id}", json={"enabled": enabled})
