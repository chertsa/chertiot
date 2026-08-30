from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def audit(db: Session, actor: str, action: str, target: str | None = None, **detail: Any) -> None:
    """Append-only audit trail (D11: minimal data — never put secrets or tokens in detail)."""
    db.add(AuditLog(actor=actor, action=action, target=target, detail=detail or None))
