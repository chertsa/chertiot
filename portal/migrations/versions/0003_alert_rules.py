"""student alert rules (M3.4)

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-02
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("device_name", sa.String(64), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("op", sa.String(2), nullable=False),
        sa.Column("threshold", sa.Float, nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("target", sa.String(320)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alert_rules_user_id", "alert_rules", ["user_id"])


def downgrade() -> None:
    op.drop_table("alert_rules")
