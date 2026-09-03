"""ChirpStack v4 REST client (via chirpstack-rest-api) for the LoRa track (M4.1).

Bootstraps a shared tenant, application, device profile and an admin API token; registers OTAA
devices. All calls go to the internal REST gateway; never exposed publicly."""

from __future__ import annotations

import os
import secrets

import httpx

REST = os.environ.get("CHIRPSTACK_REST_URL", "http://chirpstack-rest-api:8090").rstrip("/")
TENANT_NAME = "CHERT IoT"
APP_NAME = "chertiot"
PROFILE_NAME = "chertiot-eu868-otaa"


class ChirpStack:
    def __init__(self, token: str) -> None:
        self._http = httpx.Client(
            base_url=REST, headers={"Authorization": f"Bearer {token}"}, timeout=30
        )

    @staticmethod
    def login_admin(email: str = "admin", password: str = "admin") -> str:  # noqa: S107
        """Default ChirpStack admin exists on a fresh instance; used once to mint an API token."""
        r = httpx.post(
            f"{REST}/api/internal/login", json={"email": email, "password": password}, timeout=30
        )
        r.raise_for_status()
        return str(r.json()["jwt"])

    def ensure_tenant(self) -> str:
        result = self._http.get("/api/tenants", params={"limit": 100}).json().get("result", [])
        for t in result:
            if t["name"] == TENANT_NAME:
                return str(t["id"])
        body = {
            "tenant": {
                "name": TENANT_NAME,
                "canHaveGateways": True,
                "maxGatewayCount": 0,
                "maxDeviceCount": 0,
            }
        }
        return str(self._http.post("/api/tenants", json=body).json()["id"])

    def ensure_api_token(self, tenant_id: str) -> str:
        body = {"apiKey": {"name": "chertiot-portal", "tenantId": tenant_id}}
        return str(self._http.post("/api/internal/api-keys", json=body).json()["token"])

    def ensure_application(self, tenant_id: str) -> str:
        result = (
            self._http.get("/api/applications", params={"limit": 100, "tenantId": tenant_id})
            .json()
            .get("result", [])
        )
        for a in result:
            if a["name"] == APP_NAME:
                return str(a["id"])
        body = {
            "application": {
                "name": APP_NAME,
                "description": "CHERT IoT student LoRa devices",
                "tenantId": tenant_id,
            }
        }
        return str(self._http.post("/api/applications", json=body).json()["id"])

    def ensure_device_profile(self, tenant_id: str) -> str:
        result = (
            self._http.get("/api/device-profiles", params={"limit": 100, "tenantId": tenant_id})
            .json()
            .get("result", [])
        )
        for pr in result:
            if pr["name"] == PROFILE_NAME:
                return str(pr["id"])
        body = {
            "deviceProfile": {
                "name": PROFILE_NAME,
                "tenantId": tenant_id,
                "region": "EU868",
                "macVersion": "LORAWAN_1_0_3",
                "regParamsRevision": "A",
                "supportsOtaa": True,
                "uplinkInterval": 3600,
                "deviceStatusReqInterval": 1,
                "flushQueueOnActivate": True,
            }
        }
        return str(self._http.post("/api/device-profiles", json=body).json()["id"])

    def create_device(
        self, app_id: str, profile_id: str, dev_eui: str, name: str, app_key: str
    ) -> None:
        self._http.post(
            "/api/devices",
            json={
                "device": {
                    "devEui": dev_eui,
                    "name": name,
                    "applicationId": app_id,
                    "deviceProfileId": profile_id,
                    "isDisabled": False,
                }
            },
        ).raise_for_status()
        self._http.post(
            f"/api/devices/{dev_eui}/keys",
            json={"deviceKeys": {"devEui": dev_eui, "nwkKey": app_key, "appKey": app_key}},
        ).raise_for_status()

    def delete_device(self, dev_eui: str) -> None:
        self._http.delete(f"/api/devices/{dev_eui}")


def new_dev_eui() -> str:
    return secrets.token_hex(8)


def new_app_key() -> str:
    return secrets.token_hex(16)
