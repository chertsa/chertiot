"""Seed ready-to-use UAT accounts (idempotent). Reads a JSON spec from UAT_SPEC:
[{"email","password","role","cohort"}]. Creates a pre-verified Keycloak user, provisions the
student's ThingsBoard tenant + starter device, sets the portal role, and (for instructors) a class
code. Prints a summary. Operational tool — run in the portal container against the target env."""

from __future__ import annotations

import json
import os
import secrets
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db import session_factory
from app.keycloak_admin import KeycloakAdmin, KeycloakUserExistsError
from app.models import ClassCode, PortalUser, utcnow
from app.onboarding import ensure_provisioned, sysadmin_client


def main() -> int:
    spec = json.loads(os.environ["UAT_SPEC"])
    kc = KeycloakAdmin()
    sysadmin = sysadmin_client()
    out: list[dict[str, str]] = []
    try:
        with session_factory()() as db:
            for acc in spec:
                email = acc["email"].lower()
                password = acc["password"]
                role = acc.get("role", "student")
                cohort = acc.get("cohort", "uat")
                existing = kc.find_user_by_email(email)
                if existing:
                    uid = existing["id"]
                    kc._req(
                        "PUT", f"/users/{uid}", json={"emailVerified": True, "requiredActions": []}
                    )
                    kc._req(
                        "PUT",
                        f"/users/{uid}/reset-password",
                        json={"type": "password", "value": password, "temporary": False},
                    )
                else:
                    try:
                        uid = kc.create_user(
                            email, password, first_name=acc.get("first_name", "UAT")
                        )
                    except KeycloakUserExistsError:
                        uid = kc.find_user_by_email(email)["id"]  # type: ignore[index]
                    kc._req(
                        "PUT", f"/users/{uid}", json={"emailVerified": True, "requiredActions": []}
                    )

                user = db.scalar(select(PortalUser).where(PortalUser.email == email))
                if user is None:
                    user = PortalUser(email=email, kc_user_id=uid, cohort=cohort)
                    db.add(user)
                user.kc_user_id = uid
                user.cohort = cohort
                user.role = role
                user.age_attested_at = user.age_attested_at or utcnow()
                db.commit()
                ensure_provisioned(db, user, sysadmin=sysadmin)
                out.append({"email": email, "password": password, "role": role, "cohort": cohort})
                print(f"  seeded {email} ({role}, cohort={cohort})")

            # a class code owned by the first instructor, for the signup-with-code path
            instructor = next((a for a in spec if a.get("role") == "instructor"), None)
            if instructor:
                code_cohort = instructor.get("cohort", "uat")
                code = db.scalar(select(ClassCode).where(ClassCode.cohort == code_cohort))
                if code is None:
                    code = ClassCode(
                        code=f"UAT-{secrets.token_hex(2).upper()}",
                        cohort=code_cohort,
                        instructor_email=instructor["email"].lower(),
                        max_uses=100,
                        expires_at=datetime.now(UTC) + timedelta(days=180),
                    )
                    db.add(code)
                    db.commit()
                print(f"  class code for {code_cohort}: {code.code}")
    finally:
        sysadmin.close()
    print("UAT_SEED_JSON=" + json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
