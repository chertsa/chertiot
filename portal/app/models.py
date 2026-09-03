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


class FlowInstance(Base):
    """One Node-RED container per student (M3.1). State mirrors Docker; last_active drives
    culling."""

    __tablename__ = "flow_instances"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    container_name: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(16), default="running")  # running | stopped
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AlertRule(Base):
    """A student's threshold alert (M3.4): rendered into their tenant's alert rule chain."""

    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    device_name: Mapped[str] = mapped_column(String(64))
    key: Mapped[str] = mapped_column(String(64))
    op: Mapped[str] = mapped_column(String(2), default=">")  # > | < | >= | <= | ==
    threshold: Mapped[float] = mapped_column()
    action: Mapped[str] = mapped_column(String(16), default="alarm")  # alarm | email | webhook
    target: Mapped[str | None] = mapped_column(String(320))  # email address or webhook URL
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LoraDevice(Base):
    """Maps a LoRaWAN device (DevEUI) to a student's ThingsBoard device (M4.1). The lora-bridge
    uses this to route ChirpStack uplinks into the owning student's tenant."""

    __tablename__ = "lora_devices"

    dev_eui: Mapped[str] = mapped_column(String(16), primary_key=True)  # 8-byte hex
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    tb_device_name: Mapped[str] = mapped_column(String(64))
    app_key: Mapped[str] = mapped_column(String(32))  # OTAA AppKey (hex) shown to the student once
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
