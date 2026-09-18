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
    """One Node-RED container per project (D13/M5.2). State mirrors Docker; last_active drives
    culling."""

    __tablename__ = "flow_instances"

    project_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    container_name: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(16), default="running")  # running | stopped
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AlertRule(Base):
    """A project threshold alert (M3.4/M5.3): rendered into the project's alert rule chain."""

    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    device_name: Mapped[str] = mapped_column(String(64))
    key: Mapped[str] = mapped_column(String(64))
    op: Mapped[str] = mapped_column(String(2), default=">")  # > | < | >= | <= | ==
    threshold: Mapped[float] = mapped_column()
    action: Mapped[str] = mapped_column(String(16), default="alarm")  # alarm | email | webhook
    target: Mapped[str | None] = mapped_column(String(320))  # email address or webhook URL
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LoraDevice(Base):
    """Maps a LoRaWAN device (DevEUI) to a project's ThingsBoard device (M4.1/M5.4). The lora-bridge
    uses this to route ChirpStack uplinks into the owning project's tenant."""

    __tablename__ = "lora_devices"

    dev_eui: Mapped[str] = mapped_column(String(16), primary_key=True)  # 8-byte hex
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    tb_device_name: Mapped[str] = mapped_column(String(64))
    app_key: Mapped[str] = mapped_column(String(32))  # OTAA AppKey (hex) shown to the student once
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Project(Base):
    """A project = an isolated ThingsBoard TENANT (D13). Owner + members are tenant admins of it.
    The portal row is the source of truth; it mirrors to the TB tenant, a ChirpStack application,
    a per-project Node-RED instance and a Jupyter named-server."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | archived
    tb_tenant_id: Mapped[str | None] = mapped_column(String(36), index=True)
    chirpstack_application_id: Mapped[str | None] = mapped_column(String(36))
    provisioning_state: Mapped[str] = mapped_column(String(16), default="pending")
    provisioning_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProjectMember(Base):
    """A human's membership in a project. `tb_user_id` is that human's own Tenant-Admin user inside
    the project tenant (TB emails are globally unique, so it uses a synthetic address)."""

    __tablename__ = "project_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)  # portal_users.id
    role: Mapped[str] = mapped_column(String(8), default="member")  # owner | member
    tb_user_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | disabled
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProjectInvite(Base):
    """An email invitation to join a project as a member (M5.6). Accepted on the invitee's login."""

    __tablename__ = "project_invites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    invited_email: Mapped[str] = mapped_column(String(320), index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=_uuid)
    invited_by: Mapped[str] = mapped_column(String(36))  # portal_users.id of the owner
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|accepted|revoked
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProjectJoinRequest(Base):
    """A user's request to join a project (M5.6); the owner approves or denies."""

    __tablename__ = "project_join_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|approved|denied
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
