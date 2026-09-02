"""ThingsBoard REST client — the ONLY touchpoint between the portal and ThingsBoard (D10).

Sync httpx client with JWT login + refresh, retry/backoff on transport errors and 5xx, and typed
(pydantic) responses for the entities the portal manages. TB API surprises are documented inline
and mirrored in CLAUDE.md.
"""

from __future__ import annotations

import base64
import json
import time
from typing import Any, Literal, TypeVar

import httpx
from pydantic import BaseModel, ConfigDict, Field
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

# ----------------------------------------------------------------------------- models

EntityType = Literal[
    "TENANT", "TENANT_PROFILE", "USER", "CUSTOMER", "DEVICE", "DEVICE_PROFILE", "DASHBOARD"
]


class EntityId(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    # entityType is absent on a few payloads (e.g. DeviceCredentials.id is a bare {"id": uuid}).
    entity_type: EntityType | None = Field(default=None, alias="entityType")
    id: str


class TbEntity(BaseModel):
    """Base for TB entities: tolerant of extra fields, keeps raw payload for round-tripping."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: EntityId | None = None
    created_time: int | None = Field(default=None, alias="createdTime")


class TenantProfile(TbEntity):
    name: str
    description: str | None = None
    default: bool = False
    isolated_tb_rule_engine: bool = Field(default=False, alias="isolatedTbRuleEngine")
    profile_data: dict[str, Any] = Field(default_factory=dict, alias="profileData")


class Tenant(TbEntity):
    title: str
    tenant_profile_id: EntityId | None = Field(default=None, alias="tenantProfileId")
    email: str | None = None


class User(TbEntity):
    email: str
    authority: Literal["SYS_ADMIN", "TENANT_ADMIN", "CUSTOMER_USER"] = "TENANT_ADMIN"
    tenant_id: EntityId | None = Field(default=None, alias="tenantId")
    customer_id: EntityId | None = Field(default=None, alias="customerId")
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")


class Device(TbEntity):
    name: str
    type: str = "default"
    label: str | None = None
    tenant_id: EntityId | None = Field(default=None, alias="tenantId")
    device_profile_id: EntityId | None = Field(default=None, alias="deviceProfileId")


class DeviceCredentials(TbEntity):
    device_id: EntityId = Field(alias="deviceId")
    credentials_type: str = Field(alias="credentialsType")
    credentials_id: str = Field(alias="credentialsId")  # the MQTT access token for ACCESS_TOKEN


class Dashboard(TbEntity):
    title: str
    tenant_id: EntityId | None = Field(default=None, alias="tenantId")
    configuration: dict[str, Any] = Field(default_factory=dict)


class TokenPair(BaseModel):
    token: str
    refresh_token: str = Field(alias="refreshToken")


T = TypeVar("T", bound=BaseModel)


# ----------------------------------------------------------------------------- errors


class TbError(Exception):
    def __init__(self, status: int, message: str, method: str, path: str) -> None:
        super().__init__(f"{method} {path} -> {status}: {message}")
        self.status = status
        self.message = message


class TbNotFoundError(TbError):
    pass


def _is_transient(exc: BaseException) -> bool:
    return isinstance(exc, httpx.TransportError) or (
        isinstance(exc, TbError) and exc.status in (502, 503, 504)
    )


def _jwt_exp(token: str) -> float:
    """Expiry (epoch seconds) from an unverified JWT payload. TB tokens are HS512; we only read."""
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return float(json.loads(base64.urlsafe_b64decode(payload)).get("exp", 0))


# ----------------------------------------------------------------------------- client


class TbClient:
    """Authenticated ThingsBoard REST session for one principal (sysadmin or a tenant admin)."""

    REFRESH_SKEW_S = 120

    def __init__(
        self,
        base_url: str,
        *,
        username: str | None = None,
        password: str | None = None,
        token_pair: TokenPair | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._tokens = token_pair
        self._http = httpx.Client(
            base_url=f"{self.base_url}/api", timeout=timeout, transport=transport
        )

    # --- auth -----------------------------------------------------------------
    def login(self) -> TokenPair:
        if not (self._username and self._password):
            raise TbError(401, "no credentials to log in with", "POST", "/auth/login")
        r = self._http.post(
            "/auth/login", json={"username": self._username, "password": self._password}
        )
        self._raise_for_status(r, "POST", "/auth/login")
        self._tokens = TokenPair.model_validate(r.json())
        return self._tokens

    def refresh(self) -> TokenPair:
        if not self._tokens:
            return self.login()
        r = self._http.post("/auth/token", json={"refreshToken": self._tokens.refresh_token})
        if r.status_code == 401:
            return self.login()
        self._raise_for_status(r, "POST", "/auth/token")
        self._tokens = TokenPair.model_validate(r.json())
        return self._tokens

    def _auth_header(self) -> dict[str, str]:
        if self._tokens is None:
            self._tokens = self.login()
        if _jwt_exp(self._tokens.token) - time.time() < self.REFRESH_SKEW_S:
            self.refresh()
        return {"X-Authorization": f"Bearer {self._tokens.token}"}

    def impersonate(self, user_id: str) -> TbClient:
        """SYS_ADMIN only: a client acting as the given user (GET /user/{id}/token)."""
        pair = TokenPair.model_validate(self._get(f"/user/{user_id}/token"))
        return TbClient(self.base_url, token_pair=pair, transport=self._http._transport)

    # --- transport ------------------------------------------------------------
    @staticmethod
    def _raise_for_status(r: httpx.Response, method: str, path: str) -> None:
        if r.is_success:
            return
        try:
            message = r.json().get("message", r.text)
        except ValueError:
            message = r.text
        if r.status_code == 404:
            raise TbNotFoundError(404, message, method, path)
        raise TbError(r.status_code, message, method, path)

    @retry(
        retry=retry_if_exception(_is_transient),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=0.5, max=8),
        reraise=True,
    )
    def _request(self, method: str, path: str, **kw: Any) -> httpx.Response:
        r = self._http.request(method, path, headers=self._auth_header(), **kw)
        if r.status_code == 401 and self._tokens is not None:
            # Token revoked/expired server-side: refresh once and retry.
            self.refresh()
            r = self._http.request(method, path, headers=self._auth_header(), **kw)
        self._raise_for_status(r, method, path)
        return r

    def _get(self, path: str, **params: Any) -> Any:
        r = self._request("GET", path, params={k: v for k, v in params.items() if v is not None})
        return r.json() if r.content and "json" in r.headers.get("content-type", "") else r.text

    def _post(self, path: str, body: Any = None, **params: Any) -> Any:
        r = self._request("POST", path, json=body, params=params or None)
        return r.json() if r.content else None

    def _delete(self, path: str) -> None:
        self._request("DELETE", path)

    def _page(self, path: str, model: type[T], **params: Any) -> list[T]:
        params.setdefault("pageSize", 100)
        params.setdefault("page", 0)
        return [model.model_validate(d) for d in self._get(path, **params)["data"]]

    # --- tenant profiles (SYS_ADMIN) --------------------------------------------
    def list_tenant_profiles(self) -> list[TenantProfile]:
        return self._page("/tenantProfiles", TenantProfile)

    def find_tenant_profile(self, name: str) -> TenantProfile | None:
        return next((p for p in self.list_tenant_profiles() if p.name == name), None)

    def save_tenant_profile(self, profile: TenantProfile) -> TenantProfile:
        return TenantProfile.model_validate(
            self._post("/tenantProfile", profile.model_dump(by_alias=True, exclude_none=True))
        )

    def set_default_tenant_profile(self, profile_id: str) -> None:
        self._post(f"/tenantProfile/{profile_id}/default")

    # --- tenants (SYS_ADMIN) ----------------------------------------------------
    def find_tenant(self, title: str) -> Tenant | None:
        # textSearch is a substring match on title; filter to the exact one.
        return next(
            (t for t in self._page("/tenants", Tenant, textSearch=title) if t.title == title), None
        )

    def get_tenant(self, tenant_id: str) -> Tenant:
        return Tenant.model_validate(self._get(f"/tenant/{tenant_id}"))

    def save_tenant(self, tenant: Tenant) -> Tenant:
        return Tenant.model_validate(
            self._post("/tenant", tenant.model_dump(by_alias=True, exclude_none=True))
        )

    def delete_tenant(self, tenant_id: str) -> None:
        self._delete(f"/tenant/{tenant_id}")

    # --- users ------------------------------------------------------------------
    def find_tenant_user(self, tenant_id: str, email: str) -> User | None:
        users = self._page(f"/tenant/{tenant_id}/users", User, textSearch=email)
        return next((u for u in users if u.email.lower() == email.lower()), None)

    def save_user(self, user: User, *, send_activation_mail: bool = False) -> User:
        body = user.model_dump(by_alias=True, exclude_none=True)
        return User.model_validate(
            self._post("/user", body, sendActivationMail=send_activation_mail)
        )

    def get_activation_link(self, user_id: str) -> str:
        return str(self._get(f"/user/{user_id}/activationLink"))

    def activate_user(self, activate_token: str, password: str) -> TokenPair:
        r = self._http.post(
            "/noauth/activate", json={"activateToken": activate_token, "password": password}
        )
        self._raise_for_status(r, "POST", "/noauth/activate")
        return TokenPair.model_validate(r.json())

    def set_user_credentials_enabled(self, user_id: str, enabled: bool) -> None:
        self._post(f"/user/{user_id}/userCredentialsEnabled", userCredentialsEnabled=enabled)

    def delete_user(self, user_id: str) -> None:
        self._delete(f"/user/{user_id}")

    # --- devices (tenant scope) -------------------------------------------------
    def find_device(self, name: str) -> Device | None:
        try:
            return Device.model_validate(self._get("/tenant/devices", deviceName=name))
        except TbNotFoundError:
            return None

    def save_device(self, device: Device) -> Device:
        return Device.model_validate(
            self._post("/device", device.model_dump(by_alias=True, exclude_none=True))
        )

    def get_device_credentials(self, device_id: str) -> DeviceCredentials:
        return DeviceCredentials.model_validate(self._get(f"/device/{device_id}/credentials"))

    def list_devices(self) -> list[Device]:
        return self._page("/tenant/devices", Device)

    def get_device(self, device_id: str) -> Device:
        return Device.model_validate(self._get(f"/device/{device_id}"))

    def server_attributes(self, device_id: str, keys: list[str]) -> dict[str, Any]:
        """Server-scope attributes as {key: value}; TB maintains `active` and `lastActivityTime`."""
        rows = self._get(
            f"/plugins/telemetry/DEVICE/{device_id}/values/attributes/SERVER_SCOPE",
            keys=",".join(keys),
        )
        return {r["key"]: r["value"] for r in rows} if isinstance(rows, list) else {}

    def rotate_device_token(self, device_id: str, new_token: str) -> DeviceCredentials:
        """Replace the access token (old one stops working immediately)."""
        creds = self.get_device_credentials(device_id)
        body = creds.model_dump(by_alias=True, exclude_none=True)
        body["credentialsType"] = "ACCESS_TOKEN"
        body["credentialsId"] = new_token
        return DeviceCredentials.model_validate(self._post("/device/credentials", body))

    def delete_device(self, device_id: str) -> None:
        self._delete(f"/device/{device_id}")

    # --- dashboards (tenant scope) ----------------------------------------------
    def find_dashboard(self, title: str) -> Dashboard | None:
        infos = self._get("/tenant/dashboards", pageSize=100, page=0, textSearch=title)["data"]
        match = next((d for d in infos if d["title"] == title), None)
        return (
            Dashboard.model_validate(self._get(f"/dashboard/{match['id']['id']}"))
            if match
            else None
        )

    def save_dashboard(self, dashboard: Dashboard) -> Dashboard:
        body = dashboard.model_dump(by_alias=True, exclude_none=True)
        return Dashboard.model_validate(self._post("/dashboard", body))

    def delete_dashboard(self, dashboard_id: str) -> None:
        self._delete(f"/dashboard/{dashboard_id}")

    # --- rule chains (tenant scope, M3.4) -----------------------------------------
    def find_rule_chain(self, name: str) -> dict[str, Any] | None:
        data = self._get("/ruleChains", pageSize=100, page=0, textSearch=name)["data"]
        return next((rc for rc in data if rc["name"] == name), None)

    def save_rule_chain(self, rule_chain: dict[str, Any]) -> dict[str, Any]:
        return dict(self._post("/ruleChain", rule_chain))

    def save_rule_chain_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return dict(self._post("/ruleChain/metadata", metadata))

    def get_default_device_profile(self) -> dict[str, Any]:
        return dict(self._get("/deviceProfileInfo/default"))

    def get_device_profile(self, profile_id: str) -> dict[str, Any]:
        return dict(self._get(f"/deviceProfile/{profile_id}"))

    def save_device_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        return dict(self._post("/deviceProfile", profile))

    # --- telemetry (tenant scope) -----------------------------------------------
    def timeseries(
        self, device_id: str, keys: list[str], start_ts: int, end_ts: int, limit: int = 10000
    ) -> dict[str, list[dict[str, Any]]]:
        """Raw timeseries page (ms epochs); order per TB default (descending ts)."""
        data = self._get(
            f"/plugins/telemetry/DEVICE/{device_id}/values/timeseries",
            keys=",".join(keys),
            startTs=start_ts,
            endTs=end_ts,
            limit=limit,
            agg="NONE",
        )
        return dict(data) if isinstance(data, dict) else {}

    def latest_timeseries(self, device_id: str, keys: list[str]) -> dict[str, list[dict[str, Any]]]:
        data = self._get(
            f"/plugins/telemetry/DEVICE/{device_id}/values/timeseries", keys=",".join(keys)
        )
        if not isinstance(data, dict):
            return {}
        # TB API quirk: a key with no data comes back as [{"ts": now, "value": null}] — drop it.
        return {k: v for k, v in data.items() if v and v[0].get("value") is not None}

    def close(self) -> None:
        self._http.close()
