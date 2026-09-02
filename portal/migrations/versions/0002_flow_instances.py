"""per-student Node-RED instances (M3.1)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-02
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "flow_instances",
        sa.Column("user_id", sa.String(36), primary_key=True),
        sa.Column("container_name", sa.String(80), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("last_active", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("flow_instances")
