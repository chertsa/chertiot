from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import alerts as alerts_mod
from app.audit import audit
from app.db import get_db
from app.models import AlertRule, PortalUser
from app.student import as_student, require_provisioned
from app.templating import templates

router = APIRouter()


def _apply(user: PortalUser, db: Session) -> None:
    rules = list(db.scalars(select(AlertRule).where(AlertRule.user_id == user.id)))
    with as_student(user) as (_sysadmin, student):
        alerts_mod.apply_rules(student, rules)


@router.get("/alerts")
def alerts_page(request: Request, db: Session = Depends(get_db)) -> Any:
    user = require_provisioned(request, db)
    rules = list(db.scalars(select(AlertRule).where(AlertRule.user_id == user.id)))
    with as_student(user) as (_sysadmin, student):
        devices = [d.name for d in student.list_devices()]
    ctx = {"user": user, "rules": rules, "devices": devices}
    return templates.TemplateResponse(request, "alerts.html", ctx)


@router.post("/alerts")
def create_alert(
    request: Request,
    device_name: Annotated[str, Form()],
    key: Annotated[str, Form()],
    op: Annotated[str, Form()],
    threshold: Annotated[float, Form()],
    action: Annotated[str, Form()] = "alarm",
    target: Annotated[str, Form()] = "",
    db: Session = Depends(get_db),
) -> Any:
    user = require_provisioned(request, db)
    if op not in alerts_mod.OPS or action not in ("alarm", "email", "webhook"):
        raise HTTPException(status_code=422)
    if action in ("email", "webhook") and not target.strip():
        raise HTTPException(status_code=422, detail="target required")
    if action == "webhook" and not target.startswith("https://"):
        raise HTTPException(status_code=422, detail="webhook must be https")
    count = len(list(db.scalars(select(AlertRule).where(AlertRule.user_id == user.id))))
    if count >= 10:
        raise HTTPException(status_code=422, detail="rule limit reached")
    db.add(
        AlertRule(
            user_id=user.id,
            device_name=device_name.strip()[:64],
            key="".join(ch for ch in key.strip() if ch.isalnum() or ch == "_")[:64],
            op=op,
            threshold=threshold,
            action=action,
            target=target.strip() or None,
        )
    )
    db.commit()
    _apply(user, db)
    audit(
        db, user.email, "alert.create", f"{device_name}.{key} {op} {threshold}", rule_action=action
    )
    db.commit()
    return RedirectResponse("/alerts", status_code=303)


@router.post("/alerts/{rule_id}/delete")
def delete_alert(request: Request, rule_id: str, db: Session = Depends(get_db)) -> Any:
    user = require_provisioned(request, db)
    rule = db.get(AlertRule, rule_id)
    if rule is None or rule.user_id != user.id:
        raise HTTPException(status_code=404)
    db.delete(rule)
    db.commit()
    _apply(user, db)
    audit(db, user.email, "alert.delete", rule_id)
    db.commit()
    return RedirectResponse("/alerts", status_code=303)
