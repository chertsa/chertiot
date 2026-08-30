import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import audit
from app.config import get_settings
from app.db import get_db
from app.keycloak_admin import KeycloakAdmin, KeycloakError, KeycloakUserExistsError
from app.models import ClassCode, PortalUser, utcnow
from app.templating import templates

router = APIRouter()
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_kc() -> KeycloakAdmin:
    return KeycloakAdmin()


def _render(
    request: Request, errors: dict[str, str], values: dict[str, str], status: int = 200
) -> Any:
    return templates.TemplateResponse(
        request, "signup.html", {"errors": errors, "values": values}, status_code=status
    )


@router.get("/signup")
def signup_form(request: Request) -> Any:
    return _render(request, {}, {})


@router.post("/signup")
def signup_submit(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    password_confirm: Annotated[str, Form()],
    class_code: Annotated[str, Form()] = "",
    age_attested: Annotated[str, Form()] = "",
    first_name: Annotated[str, Form()] = "",
    db: Session = Depends(get_db),
    kc: KeycloakAdmin = Depends(get_kc),
) -> Any:
    email = email.strip().lower()
    class_code = class_code.strip().upper()
    values = {"email": email, "class_code": class_code, "first_name": first_name.strip()}
    errors: dict[str, str] = {}
    if not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address."
    if len(password) < 10:
        errors["password"] = "Use at least 10 characters."
    elif password != password_confirm:
        errors["password_confirm"] = "Passwords don't match."
    if age_attested != "yes":
        errors["age_attested"] = (
            "Confirm you are 18 or older, or signing up through your school's class code."
        )
    code: ClassCode | None = None
    if class_code:
        code = db.get(ClassCode, class_code)
        if code is None or not code.is_usable():
            errors["class_code"] = (
                "This class code isn't valid any more. Ask your instructor for a new one."
            )
    if db.scalar(select(PortalUser).where(PortalUser.email == email)):
        errors["email"] = "An account with this email exists. Sign in instead."
    if errors:
        return _render(request, errors, values, 422)

    try:
        kc_id = kc.create_user(email, password, first_name=values["first_name"])
    except KeycloakUserExistsError:
        return _render(
            request, {"email": "An account with this email exists. Sign in instead."}, values, 422
        )
    except KeycloakError as e:
        # Keycloak owns the password policy; surface its message verbatim.
        return _render(request, {"password": e.message}, values, 422)

    s = get_settings()
    kc.send_verify_email(kc_id, f"{s.portal_public_url}/auth/verified")
    user = PortalUser(
        email=email,
        kc_user_id=kc_id,
        class_code=code.code if code else None,
        cohort=code.cohort if code else "community",
        age_attested_at=utcnow(),
    )
    if code:
        code.uses += 1
    db.add(user)
    audit(db, email, "signup", cohort=user.cohort, class_code=user.class_code)
    db.commit()
    return RedirectResponse(f"/signup/check-email?email={email}", status_code=303)


@router.get("/signup/check-email")
def check_email(request: Request, email: str = "") -> Any:
    return templates.TemplateResponse(request, "check_email.html", {"email": email})
