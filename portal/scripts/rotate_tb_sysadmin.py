"""Rotate the ThingsBoard sysadmin password to the value in the environment (idempotent).

Fresh TB installs ship sysadmin@thingsboard.org / 'sysadmin'. Deploys generate a real password
into .env; this script makes TB match it: if login with the target password works, done; else it
logs in with the default and changes it."""

from __future__ import annotations

import os
import sys

import httpx

TB = os.environ.get("TB_ADMIN_URL", "http://tb:8080").rstrip("/")
EMAIL = os.environ["TB_SYSADMIN_EMAIL"]
TARGET = os.environ["TB_SYSADMIN_PASSWORD"]
DEFAULT = "sysadmin"  # noqa: S105 — ThingsBoard's documented install default


def login(password: str) -> str | None:
    r = httpx.post(
        f"{TB}/api/auth/login", json={"username": EMAIL, "password": password}, timeout=30
    )
    return r.json()["token"] if r.status_code == 200 else None


def main() -> int:
    if login(TARGET):
        print("sysadmin password already rotated")
        return 0
    token = login(DEFAULT)
    if not token:
        print("ERROR: neither the target nor the default sysadmin password works", file=sys.stderr)
        return 1
    r = httpx.post(
        f"{TB}/api/auth/changePassword",
        headers={"X-Authorization": f"Bearer {token}"},
        json={"currentPassword": DEFAULT, "newPassword": TARGET},
        timeout=30,
    )
    if r.status_code >= 400:
        print(f"ERROR: changePassword -> {r.status_code}: {r.text[:200]}", file=sys.stderr)
        return 1
    print("sysadmin password rotated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
