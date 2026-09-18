"""M5.1 acceptance against a live TB: creating a project provisions an isolated TB tenant with the
owner as tenant admin, quotas, and a starter dashboard — idempotent, partial-failure safe, and the
project session can create a device and receive its telemetry over MQTT."""

import json
import os
import uuid

import paho.mqtt.client as mqtt
import pytest
from sqlalchemy.orm import Session

from app import project as project_mod
from app.models import PortalUser, Project
from app.project import as_project, create_project, delete_project, membership
from app.tb_client import Device, TbClient, TbError

MQTT_HOST = os.environ.get("TB_MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("TB_MQTT_PORT", "1883"))


def _user(db: Session) -> PortalUser:
    u = PortalUser(
        email=f"it-{uuid.uuid4().hex[:8]}@test.chertiot.local", kc_user_id=uuid.uuid4().hex
    )
    db.add(u)
    db.commit()
    return u


def _cleanup(sysadmin: TbClient, project: Project) -> None:
    if project.tb_tenant_id:
        try:
            sysadmin.delete_tenant(project.tb_tenant_id)
        except TbError:
            pass


def test_create_project_provisions_tenant_owner_dashboard(sysadmin: TbClient, db: Session) -> None:
    user = _user(db)
    project = create_project(db, user, "Greenhouse monitor", "hello")
    try:
        assert project.provisioning_state == "provisioned", project.provisioning_error
        assert project.tb_tenant_id
        owner = membership(db, project.id, user.id)
        assert owner and owner.role == "owner" and owner.tb_user_id

        tenant = sysadmin.get_tenant(project.tb_tenant_id)
        profile = sysadmin.find_tenant_profile("chertiot-student")
        assert profile and profile.default and tenant.tenant_profile_id == profile.id
        with as_project(owner) as (_s, session):
            assert session.find_dashboard("My devices")
    finally:
        _cleanup(sysadmin, project)


def test_partial_failure_is_repaired_on_retry(
    sysadmin: TbClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = _user(db)

    def boom(*a: object, **k: object) -> object:
        raise TbError(503, "simulated outage", "POST", "/dashboard")

    monkeypatch.setattr(project_mod, "ensure_starter_dashboard", boom)
    project = create_project(db, user, "Weather", None)
    try:
        assert project.provisioning_state == "failed"
        assert project.tb_tenant_id  # tenant + owner user already exist
        monkeypatch.undo()
        owner = membership(db, project.id, user.id)
        assert owner
        assert project_mod.retry_provision(db, project, user, owner)
        assert project.provisioning_state == "provisioned"
    finally:
        _cleanup(sysadmin, project)


def test_delete_project_removes_tenant(sysadmin: TbClient, db: Session) -> None:
    user = _user(db)
    project = create_project(db, user, "Throwaway", None)
    tenant_id = project.tb_tenant_id
    assert tenant_id
    delete_project(db, project, user.email)
    assert db.get(Project, project.id) is None
    assert sysadmin.find_tenant("Throwaway") is None or sysadmin.get_tenant(tenant_id) is None


def test_mqtt_telemetry_reaches_a_project_device(sysadmin: TbClient, db: Session) -> None:
    user = _user(db)
    project = create_project(db, user, "Telemetry", None)
    try:
        owner = membership(db, project.id, user.id)
        assert owner
        with as_project(owner) as (_s, session):
            device = session.save_device(Device(name="probe", type="default"))
            assert device.id
            token = session.get_device_credentials(device.id.id).credentials_id
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        c.username_pw_set(token)
        c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
        c.loop_start()
        info = c.publish("v1/devices/me/telemetry", json.dumps({"temperature": 21.5}), qos=1)
        info.wait_for_publish(timeout=10)
        c.disconnect()
        c.loop_stop()
        assert info.is_published()
    finally:
        _cleanup(sysadmin, project)
