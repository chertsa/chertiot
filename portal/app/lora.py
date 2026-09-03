"""LoRa registration flow (M4.1): create a TB device + a ChirpStack device and map them."""

from __future__ import annotations

import os

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.chirpstack import ChirpStack, new_app_key, new_dev_eui
from app.models import LoraDevice, PortalUser
from app.provisioning import require_id
from app.student import as_student
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


def register(db: Session, user: PortalUser) -> LoraDevice:
    """Create a LoRa device: a ChirpStack OTAA device + a matching TB device, mapped by DevEUI."""
    cs, tenant_id = client(db)
    app_id = cs.ensure_application(tenant_id)
    profile_id = cs.ensure_device_profile(tenant_id)
    dev_eui = new_dev_eui()
    app_key = new_app_key()
    tb_name = f"lora-{dev_eui[:6]}"
    with as_student(user) as (_sysadmin, student):
        device = student.find_device(tb_name) or student.save_device(
            Device(name=tb_name, label="LoRaWAN device", type="lora")
        )
        require_id(device, "device")
    cs.create_device(app_id, profile_id, dev_eui, tb_name, app_key)
    mapping = LoraDevice(dev_eui=dev_eui, user_id=user.id, tb_device_name=tb_name, app_key=app_key)
    db.add(mapping)
    db.commit()
    return mapping
