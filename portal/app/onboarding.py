"""Runs TB provisioning for a portal user after a verified login. Idempotent; repairs drift."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.audit import audit
from app.config import Settings, get_settings
from app.models import PortalUser, utcnow
from app.provisioning import provision_student
from app.tb_client import TbClient

log = logging.getLogger(__name__)


def sysadmin_client(settings: Settings | None = None) -> TbClient:
    s = settings or get_settings()
    return TbClient(s.tb_admin_url, username=s.tb_sysadmin_email, password=s.tb_sysadmin_password)


def ensure_provisioned(db: Session, user: PortalUser, *, sysadmin: TbClient | None = None) -> bool:
    """Provision (or repair) the user's TB tenant. Returns True on success; records failures on
    the user row instead of raising so login still succeeds and the home page can offer a retry."""
    client = sysadmin or sysadmin_client()
    try:
        result = provision_student(client, user.email)
    except Exception as e:  # noqa: BLE001 — any TB/transport failure is a provisioning failure
        log.exception("provisioning failed for %s", user.email)
        user.provisioning_state = "failed"
        user.provisioning_error = str(e)[:500]
        audit(db, "system", "provision.failed", user.email, error=str(e)[:200])
        db.commit()
        return False
    finally:
        if sysadmin is None:
            client.close()
    changed = user.provisioning_state != "provisioned" or any(result.created.values())
    user.tb_tenant_id, user.tb_user_id = result.tenant_id, result.user_id
    user.provisioning_state, user.provisioning_error = "provisioned", None
    if changed:
        audit(db, "system", "provision.ok", user.email, created=result.created)
    user.last_login_at = utcnow()
    db.commit()
    return True
