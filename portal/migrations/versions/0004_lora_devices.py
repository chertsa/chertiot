"""lora device mapping (M4.1)

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lora_devices",
        sa.Column("dev_eui", sa.String(16), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("tb_device_name", sa.String(64), nullable=False),
        sa.Column("app_key", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lora_devices_user_id", "lora_devices", ["user_id"])


def downgrade() -> None:
    op.drop_table("lora_devices")
