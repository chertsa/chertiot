"""Bootstrap ChirpStack (M4.1): tenant, application, device profile, and an API token stored in
the portal DB as a singleton setting. Idempotent. Run in the portal container during deploy."""

from __future__ import annotations

import sys

from app.chirpstack import ChirpStack, login_admin
from app.db import session_factory
from app.models import ClassCode  # noqa: F401  (ensure metadata import side effects)


def _get_setting(db, key):  # noqa: ANN001, ANN202
    from sqlalchemy import text

    from app.models import AuditLog  # noqa: F401

    row = db.execute(text("SELECT value FROM lora_settings WHERE key=:k"), {"k": key}).first()
    return row[0] if row else None


def main() -> int:
    from sqlalchemy import text

    with session_factory()() as db:
        db.execute(
            text(
                "CREATE TABLE IF NOT EXISTS lora_settings (key VARCHAR(32) PRIMARY KEY, value TEXT)"
            )
        )
        db.commit()
        existing = _get_setting(db, "api_token")
        admin_jwt = login_admin()
        cs = ChirpStack(admin_jwt)
        tenant_id = cs.ensure_tenant()
        cs.ensure_application(tenant_id)
        cs.ensure_device_profile(tenant_id)
        if not existing:
            token = cs.create_admin_api_key()
            db.execute(
                text(
                    "INSERT INTO lora_settings (key, value) VALUES ('api_token', :v) "
                    "ON CONFLICT (key) DO UPDATE SET value=:v"
                ),
                {"v": token},
            )
        db.execute(
            text(
                "INSERT INTO lora_settings (key, value) VALUES ('tenant_id', :v) "
                "ON CONFLICT (key) DO UPDATE SET value=:v"
            ),
            {"v": tenant_id},
        )
        db.commit()
    print("chirpstack bootstrapped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
