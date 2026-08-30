"""CLI: create/list class codes (instructor UI arrives in M3.3).

make class-code CODE=CS101-F26 COHORT=cs101-fall26 INSTRUCTOR=prof@uni.edu
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db import session_factory
from app.models import ClassCode


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create")
    c.add_argument("code")
    c.add_argument("--cohort", required=True)
    c.add_argument("--instructor", required=True)
    c.add_argument("--max-uses", type=int, default=100)
    c.add_argument("--days", type=int, default=180)
    sub.add_parser("list")
    a = p.parse_args()
    with session_factory()() as db:
        if a.cmd == "create":
            code = db.get(ClassCode, a.code.upper()) or ClassCode(code=a.code.upper())
            code.cohort, code.instructor_email, code.max_uses = a.cohort, a.instructor, a.max_uses
            code.expires_at = datetime.now(UTC) + timedelta(days=a.days)
            code.active = True
            db.add(code)
            db.commit()
            print(
                f"class code {code.code}: cohort={code.cohort} expires={code.expires_at:%Y-%m-%d}"
            )
        else:
            for code in db.scalars(select(ClassCode)):
                print(
                    f"{code.code:<16} {code.cohort:<20} "
                    f"{code.uses}/{code.max_uses} active={code.active}"
                )
    return 0


if __name__ == "__main__":
    sys.exit(main())
