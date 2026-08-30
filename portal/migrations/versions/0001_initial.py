"""portal users, class codes, audit log (M1.1)

Revision ID: 0001
Revises:
Create Date: 2026-08-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portal_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("kc_user_id", sa.String(36)),
        sa.Column("tb_tenant_id", sa.String(36)),
        sa.Column("tb_user_id", sa.String(36)),
        sa.Column("class_code", sa.String(32)),
        sa.Column("cohort", sa.String(64), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("provisioning_state", sa.String(16), nullable=False),
        sa.Column("provisioning_error", sa.Text),
        sa.Column("age_attested_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_portal_users_email", "portal_users", ["email"], unique=True)
    op.create_index("ix_portal_users_kc_user_id", "portal_users", ["kc_user_id"], unique=True)
    op.create_index("ix_portal_users_tb_tenant_id", "portal_users", ["tb_tenant_id"])
    op.create_index("ix_portal_users_class_code", "portal_users", ["class_code"])
    op.create_table(
        "class_codes",
        sa.Column("code", sa.String(32), primary_key=True),
        sa.Column("cohort", sa.String(64), nullable=False),
        sa.Column("instructor_email", sa.String(320), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False),
        sa.Column("max_uses", sa.Integer, nullable=False),
        sa.Column("uses", sa.Integer, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_class_codes_instructor_email", "class_codes", ["instructor_email"])
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(320), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target", sa.String(320)),
        sa.Column("detail", sa.JSON),
    )
    op.create_index("ix_audit_log_ts", "audit_log", ["ts"])
    op.create_index("ix_audit_log_actor", "audit_log", ["actor"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("class_codes")
    op.drop_table("portal_users")
