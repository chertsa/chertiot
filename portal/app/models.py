"""Portal-owned state (D10: everything about TB entities is *references*, never copies)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class PortalUser(Base):
    __tablename__ = "portal_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    kc_user_id: Mapped[str | None] = mapped_column(String(36), unique=True, index=True)
    tb_tenant_id: Mapped[str | None] = mapped_column(String(36), index=True)
    tb_user_id: Mapped[str | None] = mapped_column(String(36))
    class_code: Mapped[str | None] = mapped_column(String(32), index=True)
    cohort: Mapped[str] = mapped_column(String(64), default="community")
    # student | instructor | admin
    role: Mapped[str] = mapped_column(String(16), default="student")
    provisioning_state: Mapped[str] = mapped_column(String(16), default="pending")
    provisioning_error: Mapped[str | None] = mapped_column(Text)
    age_attested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClassCode(Base):
    """Instructor-generated code routing signups to a cohort (D4 class tenant: Phase 3)."""

    __tablename__ = "class_codes"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    cohort: Mapped[str] = mapped_column(String(64))
    instructor_email: Mapped[str] = mapped_column(String(320), index=True)
    active: Mapped[bool] = mapped_column(default=True)
    max_uses: Mapped[int] = mapped_column(Integer, default=100)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def is_usable(self, now: datetime | None = None) -> bool:
        now = now or utcnow()
        expired = self.expires_at is not None and self.expires_at.replace(tzinfo=UTC) < now
        return self.active and not expired and self.uses < self.max_uses


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(320), index=True)  # email or "system"
    action: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str | None] = mapped_column(String(320))
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON)
