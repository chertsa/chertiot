"""LoRa registration flow (M4.1): create a TB device + a ChirpStack device and map them."""

from __future__ import annotations

import os

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.chirpstack import ChirpStack, new_app_key, new_dev_eui
from app.models import LoraDevice, Project, ProjectMember
from app.project import as_project
from app.provisioning import require_id
from app.tb_client import Device


def enabled() -> bool:
    return os.environ.get("LORA_ENABLED", "false").lower() == "true"


def _setting(db: Session, key: str) -> str | None:
    row = db.execute(text("SELECT value FROM lora_settings WHERE key=:k"), {"k": key}).first()
    return row[0] if row else None


def client(db: Session) -> tuple[ChirpStack, str]:
    token = _setting(db, "api_token")
    tenant_id = _setting(db, "tenant_id")
    if not token or not tenant_id:
        raise RuntimeError("ChirpStack not bootstrapped")
    return ChirpStack(token), tenant_id


def register(db: Session, project: Project, member: ProjectMember) -> LoraDevice:
    """Create a LoRa device in a PROJECT: a ChirpStack OTAA device (in the project's own ChirpStack
    application) + a matching TB device in the project tenant, mapped by DevEUI."""
    cs, tenant_id = client(db)
    app_id = cs.ensure_application(tenant_id, name=project.slug)
    profile_id = cs.ensure_device_profile(tenant_id)
    dev_eui = new_dev_eui()
    app_key = new_app_key()
    tb_name = f"lora-{dev_eui[:6]}"
    with as_project(member) as (_sysadmin, session):
        device = session.find_device(tb_name) or session.save_device(
            Device(name=tb_name, label="LoRaWAN device", type="lora")
        )
        require_id(device, "device")
    cs.create_device(app_id, profile_id, dev_eui, tb_name, app_key)
    if not project.chirpstack_application_id:
        project.chirpstack_application_id = app_id
    mapping = LoraDevice(
        dev_eui=dev_eui, project_id=project.id, tb_device_name=tb_name, app_key=app_key
    )
    db.add(mapping)
    db.commit()
    return mapping
