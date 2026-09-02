"""CLI: grant/revoke portal roles.  make grant-role EMAIL=x@y ROLE=instructor"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from app.db import session_factory
from app.models import PortalUser


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("email")
    p.add_argument("role", choices=["student", "instructor", "admin"])
    a = p.parse_args()
    with session_factory()() as db:
        user = db.scalar(select(PortalUser).where(PortalUser.email == a.email.lower()))
        if user is None:
            print("no such user", file=sys.stderr)
            return 1
        user.role = a.role
        db.commit()
        print(f"{user.email} -> {a.role}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
