"""CLI: provision (or repair) a student tenant and print the starter device token.

make provision EMAIL=student@example.com
"""

from __future__ import annotations

import argparse
import sys

from app.config import get_settings
from app.provisioning import delete_student, provision_student, suspend_student
from app.tb_client import TbClient


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("email")
    p.add_argument("--first-name")
    p.add_argument("--last-name")
    p.add_argument("--suspend", action="store_true")
    p.add_argument("--unsuspend", action="store_true")
    p.add_argument("--delete", action="store_true", help="delete the whole tenant (irreversible)")
    a = p.parse_args()
    s = get_settings()
    sysadmin = TbClient(
        s.tb_admin_url, username=s.tb_sysadmin_email, password=s.tb_sysadmin_password
    )
    if a.delete:
        print("deleted" if delete_student(sysadmin, a.email) else "no such tenant")
        return 0
    if a.suspend or a.unsuspend:
        suspend_student(sysadmin, a.email, suspended=a.suspend)
        print("suspended" if a.suspend else "unsuspended")
        return 0
    r = provision_student(sysadmin, a.email, first_name=a.first_name, last_name=a.last_name)
    print(f"tenant     {r.tenant_id}  (created={r.created['tenant']})")
    print(f"user       {r.user_id}  (created={r.created['user']})")
    print(f"dashboard  {r.dashboard_id}  (created={r.created['dashboard']})")
    print(f"device     {r.device_id}  (created={r.created['device']})")
    print(f"MQTT access token: {r.device_access_token}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
