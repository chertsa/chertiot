"""Idempotent student provisioning against ThingsBoard (M0.4, D4/D5).

Every step is find-then-create, so a partial failure is repaired by simply running again.
Tenant-scoped steps (dashboard, device) run as the student's tenant admin via sysadmin
impersonation — never by touching TB's database (D10).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.tb_client import (
    Dashboard,
    Device,
    TbClient,
    TbEntity,
    TbError,
    Tenant,
    TenantProfile,
    User,
)

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates-tb"
STUDENT_PROFILE_TEMPLATE = TEMPLATES_DIR / "tenant-profile-student.json"
STARTER_DASHBOARD_TEMPLATE = TEMPLATES_DIR / "starter-dashboard.json"
STARTER_DEVICE_NAME = "my-first-device"


class ProvisioningError(RuntimeError):
    """A TB entity came back without an id — should never happen; fail loudly, never guess."""


def require_id(entity: TbEntity, what: str) -> str:
    if entity.id is None:
        raise ProvisioningError(f"{what} has no id: {entity!r}")
    return entity.id.id


def load_template(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text()))


def student_profile_spec(settings: Settings | None = None) -> TenantProfile:
    """Template quotas with env overrides (TB_QUOTA_*) applied."""
    settings = settings or get_settings()
    spec = load_template(STUDENT_PROFILE_TEMPLATE)
    conf = spec["profileData"]["configuration"]
    if settings.tb_quota_max_devices is not None:
        conf["maxDevices"] = settings.tb_quota_max_devices
    if settings.tb_quota_device_msg_rate:
        conf["transportDeviceMsgRateLimit"] = settings.tb_quota_device_msg_rate
        conf["transportDeviceTelemetryMsgRateLimit"] = settings.tb_quota_device_msg_rate
    return TenantProfile.model_validate(spec)


def ensure_student_profile(sysadmin: TbClient, settings: Settings | None = None) -> TenantProfile:
    """Create/update the student tenant profile and make it the default (so tenants auto-created by
    the Keycloak login mapper get the quotas too)."""
    spec = student_profile_spec(settings)
    existing = sysadmin.find_tenant_profile(spec.name)
    if existing:
        spec.id = existing.id
        spec.created_time = existing.created_time
    # TB API quirk: POST /tenantProfile with default=true fails while another default exists;
    # save without the flag, then promote via /tenantProfile/{id}/default.
    spec.default = existing.default if existing else False
    saved = sysadmin.save_tenant_profile(spec)
    if not saved.default:
        sysadmin.set_default_tenant_profile(require_id(saved, "tenant profile"))
    return saved


@dataclass
class ProvisionResult:
    tenant_id: str
    user_id: str
    dashboard_id: str
    device_id: str
    device_access_token: str
    created: dict[str, bool]


def ensure_tenant(sysadmin: TbClient, email: str, profile: TenantProfile) -> tuple[Tenant, bool]:
    """Find-or-create the student's tenant and make sure it is on the student profile (a tenant
    auto-created by the Keycloak login mapper may predate the profile)."""
    require_id(profile, "tenant profile")
    tenant = sysadmin.find_tenant(email)
    if tenant:
        if tenant.tenant_profile_id != profile.id:
            tenant.tenant_profile_id = profile.id
            tenant = sysadmin.save_tenant(tenant)
        return tenant, False
    tenant = sysadmin.save_tenant(Tenant(title=email, email=email, tenantProfileId=profile.id))
    return tenant, True


def ensure_tenant_admin(
    sysadmin: TbClient, tenant: Tenant, email: str, first_name: str | None, last_name: str | None
) -> tuple[User, bool]:
    tenant_id = require_id(tenant, "tenant")
    user = sysadmin.find_tenant_user(tenant_id, email)
    if user:
        return user, False
    user = sysadmin.save_user(
        User(
            email=email,
            authority="TENANT_ADMIN",
            tenantId=tenant.id,
            firstName=first_name,
            lastName=last_name,
        )
    )
    return user, True


def ensure_starter_dashboard(
    tenant_client: TbClient, *, reset: bool = False
) -> tuple[Dashboard, bool]:
    spec = Dashboard.model_validate(load_template(STARTER_DASHBOARD_TEMPLATE))
    existing = tenant_client.find_dashboard(spec.title)
    if existing and not reset:
        return existing, False
    if existing:
        spec.id = existing.id
        spec.created_time = existing.created_time
    return tenant_client.save_dashboard(spec), existing is None


def ensure_starter_device(tenant_client: TbClient) -> tuple[Device, bool]:
    device = tenant_client.find_device(STARTER_DEVICE_NAME)
    if device:
        return device, False
    device = tenant_client.save_device(
        Device(name=STARTER_DEVICE_NAME, label="My first device", type="default")
    )
    return device, True


def provision_student(
    sysadmin: TbClient,
    email: str,
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    settings: Settings | None = None,
) -> ProvisionResult:
    """Fresh student tenant with quotas + starter dashboard + starter device. Safe to rerun."""
    created: dict[str, bool] = {}
    profile = ensure_student_profile(sysadmin, settings)
    tenant, created["tenant"] = ensure_tenant(sysadmin, email, profile)
    user, created["user"] = ensure_tenant_admin(sysadmin, tenant, email, first_name, last_name)
    tenant_id, user_id = require_id(tenant, "tenant"), require_id(user, "user")

    as_student = sysadmin.impersonate(user_id)
    try:
        dashboard, created["dashboard"] = ensure_starter_dashboard(as_student)
        device, created["device"] = ensure_starter_device(as_student)
        dashboard_id, device_id = require_id(dashboard, "dashboard"), require_id(device, "device")
        creds = as_student.get_device_credentials(device_id)
    finally:
        as_student.close()

    return ProvisionResult(
        tenant_id=tenant_id,
        user_id=user_id,
        dashboard_id=dashboard_id,
        device_id=device_id,
        device_access_token=creds.credentials_id,
        created=created,
    )


def suspend_student(sysadmin: TbClient, email: str, *, suspended: bool = True) -> None:
    """TB-side half of 'suspend' (D6): disables the user's TB credentials, which blocks password
    and refresh-token logins. It does NOT invalidate live JWTs, sysadmin impersonation, or
    Keycloak (OAuth2) logins — the authoritative switch is disabling the user in Keycloak (M3.3).
    Kept so a suspended student cannot fall back to a TB-local password."""
    tenant = sysadmin.find_tenant(email)
    if not tenant or tenant.id is None:
        return
    user = sysadmin.find_tenant_user(tenant.id.id, email)
    if not user or user.id is None:
        return
    try:
        sysadmin.set_user_credentials_enabled(user.id.id, not suspended)
    except TbError as e:
        # TB API quirk: re-enabling credentials of a user that never set a TB password fails with
        # 400 "Enabled user credentials should have password!". Such a user (portal-created, logs in
        # only via Keycloak) has nothing to re-enable, so this is a no-op, not a failure.
        if not (suspended is False and e.status == 400 and "password" in e.message.lower()):
            raise


def delete_student(sysadmin: TbClient, email: str) -> bool:
    """Delete the whole student tenant (devices, dashboards, users, telemetry). Irreversible."""
    tenant = sysadmin.find_tenant(email)
    if not tenant or tenant.id is None:
        return False
    sysadmin.delete_tenant(tenant.id.id)
    return True
