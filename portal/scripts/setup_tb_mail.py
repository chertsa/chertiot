"""Configure ThingsBoard's system SMTP (admin settings) from the SMTP_* env (M3.4).

Needed for the email alert action (TbSendEmailNode useSystemSmtpSettings) and TB's own password
reset. Idempotent. Uses the platform's SMTP2GO relay — same as Keycloak/portal."""

from __future__ import annotations

import os
import sys

import httpx

TB = os.environ.get("TB_ADMIN_URL", "http://tb:8080").rstrip("/")


def main() -> int:
    host = os.environ.get("SMTP_HOST", "")
    if not host:
        print("SMTP_HOST empty — skipping TB mail config")
        return 0
    r = httpx.post(
        f"{TB}/api/auth/login",
        json={
            "username": os.environ["TB_SYSADMIN_EMAIL"],
            "password": os.environ["TB_SYSADMIN_PASSWORD"],
        },
        timeout=30,
    )
    r.raise_for_status()
    hdr = {"X-Authorization": f"Bearer {r.json()['token']}"}
    settings = {
        "key": "mail",
        "jsonValue": {
            "mailFrom": os.environ.get("SMTP_FROM", "no-reply@chertiot.com"),
            "smtpProtocol": "smtp",
            "smtpHost": host,
            "smtpPort": int(os.environ.get("SMTP_PORT", "2525")),
            "timeout": 10000,
            "enableTls": os.environ.get("SMTP_STARTTLS", "true").lower() == "true",
            "tlsVersion": "TLSv1.2",
            "enableProxy": False,
            "username": os.environ.get("SMTP_USER", ""),
            "password": os.environ.get("SMTP_PASSWORD", ""),
        },
    }
    resp = httpx.post(f"{TB}/api/admin/settings", headers=hdr, json=settings, timeout=30)
    if resp.status_code >= 400:
        print(f"ERROR: TB mail settings -> {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
        return 1
    print("TB system SMTP configured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
