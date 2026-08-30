"""M0.4 acceptance against local TB: fresh tenant with quotas + starter dashboard + device
token, idempotent, partial-failure safe, and telemetry over MQTT lands on the starter device."""

import json
import os
import time

import paho.mqtt.client as mqtt
import pytest

from app import provisioning
from app.config import Settings
from app.provisioning import (
    STARTER_DEVICE_NAME,
    delete_student,
    provision_student,
    suspend_student,
)
from app.tb_client import TbClient, TbError, Tenant

MQTT_HOST = os.environ.get("TB_MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("TB_MQTT_PORT", "1883"))


def settings() -> Settings:
    return Settings(portal_secret_key="t", portal_database_url="postgresql://t")


def test_provision_is_idempotent(sysadmin: TbClient, student_email: str) -> None:
    first = provision_student(sysadmin, student_email, first_name="Test", settings=settings())
    assert all(first.created.values()), first.created
    second = provision_student(sysadmin, student_email, settings=settings())
    assert not any(second.created.values()), second.created
    assert (first.tenant_id, first.user_id, first.dashboard_id, first.device_id) == (
        second.tenant_id,
        second.user_id,
        second.dashboard_id,
        second.device_id,
    )
    assert first.device_access_token == second.device_access_token

    tenant = sysadmin.get_tenant(first.tenant_id)
    profile = sysadmin.find_tenant_profile("chertiot-student")
    assert profile and profile.default and tenant.tenant_profile_id == profile.id
    assert profile.profile_data["configuration"]["maxDevices"] == 10


def test_partial_failure_is_repaired_on_rerun(
    sysadmin: TbClient, student_email: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*a: object, **k: object) -> object:
        raise TbError(503, "simulated outage mid-provision", "POST", "/dashboard")

    monkeypatch.setattr(provisioning, "ensure_starter_dashboard", boom)
    with pytest.raises(TbError):
        provision_student(sysadmin, student_email, settings=settings())
    # Tenant + user exist, dashboard/device don't.
    tenant = sysadmin.find_tenant(student_email)
    assert tenant and tenant.id
    assert sysadmin.find_tenant_user(tenant.id.id, student_email)

    monkeypatch.undo()
    r = provision_student(sysadmin, student_email, settings=settings())
    assert r.created == {"tenant": False, "user": False, "dashboard": True, "device": True}


def test_mqtt_telemetry_reaches_starter_device(sysadmin: TbClient, student_email: str) -> None:
    r = provision_student(sysadmin, student_email, settings=settings())
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    c.username_pw_set(r.device_access_token)
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    info = c.publish(
        "v1/devices/me/telemetry", json.dumps({"temperature": 21.5, "humidity": 40}), qos=1
    )
    info.wait_for_publish(timeout=10)
    c.disconnect()
    c.loop_stop()
    assert info.is_published()

    as_student = sysadmin.impersonate(r.user_id)
    try:
        for _ in range(20):
            latest = as_student.latest_timeseries(r.device_id, ["temperature", "humidity"])
            if latest.get("temperature"):
                break
            time.sleep(0.5)
        assert latest["temperature"][0]["value"] == "21.5"
        # The starter dashboard alias resolves every device in the tenant, so this one is on it.
        dash = as_student.find_dashboard("My devices")
        assert dash is not None
        alias = next(iter(dash.configuration["entityAliases"].values()))
        expected = {"type": "entityType", "resolveMultiple": True, "entityType": "DEVICE"}
        assert alias["filter"] == expected
        assert any(d.name == STARTER_DEVICE_NAME for d in as_student.list_devices())
    finally:
        as_student.close()


def test_suspend_and_delete(sysadmin: TbClient, student_email: str) -> None:
    r = provision_student(sysadmin, student_email, settings=settings())

    def creds_enabled() -> bool:
        info = sysadmin._get(f"/user/{r.user_id}")["additionalInfo"]
        return bool(info.get("userCredentialsEnabled", True))

    suspend_student(sysadmin, student_email)
    assert creds_enabled() is False
    # Never-activated (Keycloak-only) user: unsuspend is a documented no-op, must not raise.
    suspend_student(sysadmin, student_email, suspended=False)
    assert creds_enabled() is False
    assert delete_student(sysadmin, student_email) is True
    assert sysadmin.find_tenant(student_email) is None
    assert delete_student(sysadmin, student_email) is False  # idempotent


def test_existing_tenant_is_moved_onto_student_profile(
    sysadmin: TbClient, student_email: str
) -> None:
    """Tenants auto-created by the Keycloak login mapper get whatever profile was default at the
    time; provisioning must repair that."""
    stock = next(p for p in sysadmin.list_tenant_profiles() if p.name == "Default")
    pre = sysadmin.save_tenant(Tenant(title=student_email, tenantProfileId=stock.id))
    assert pre.tenant_profile_id == stock.id
    r = provision_student(sysadmin, student_email, settings=settings())
    assert r.created["tenant"] is False
    student = sysadmin.find_tenant_profile("chertiot-student")
    assert student and sysadmin.get_tenant(r.tenant_id).tenant_profile_id == student.id
