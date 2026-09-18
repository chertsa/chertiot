"""project-centric model (D13 / M5.1): Project = TB tenant; owner+members

Adds projects, project_members, project_invites, project_join_requests and re-grains
flow_instances / alert_rules / lora_devices from user_id to project_id. Build phase: no data to
preserve, so the re-grained columns are dropped and recreated.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-18
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(48), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("tb_tenant_id", sa.String(36), nullable=True),
        sa.Column("chirpstack_application_id", sa.String(36), nullable=True),
        sa.Column("provisioning_state", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("provisioning_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_projects_slug", "projects", ["slug"], unique=True)
    op.create_index("ix_projects_tb_tenant_id", "projects", ["tb_tenant_id"])

    op.create_table(
        "project_members",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(8), nullable=False, server_default="member"),
        sa.Column("tb_user_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"])
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"])
    op.create_index(
        "uq_project_members_project_user", "project_members", ["project_id", "user_id"], unique=True
    )

    op.create_table(
        "project_invites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("invited_email", sa.String(320), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("invited_by", sa.String(36), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_project_invites_project_id", "project_invites", ["project_id"])
    op.create_index("ix_project_invites_invited_email", "project_invites", ["invited_email"])
    op.create_index("ix_project_invites_token", "project_invites", ["token"], unique=True)

    op.create_table(
        "project_join_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_project_join_requests_project_id", "project_join_requests", ["project_id"])
    op.create_index("ix_project_join_requests_user_id", "project_join_requests", ["user_id"])

    # Re-grain user_id -> project_id (build phase: no data preserved).
    # flow_instances PK was user_id → recreate the table keyed by project_id.
    op.drop_table("flow_instances")
    op.create_table(
        "flow_instances",
        sa.Column("project_id", sa.String(36), primary_key=True),
        sa.Column("container_name", sa.String(80), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="running"),
        sa.Column("last_active", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.drop_index("ix_alert_rules_user_id", table_name="alert_rules")
    with op.batch_alter_table("alert_rules") as b:
        b.drop_column("user_id")
        b.add_column(sa.Column("project_id", sa.String(36), nullable=False, server_default=""))
    op.create_index("ix_alert_rules_project_id", "alert_rules", ["project_id"])

    op.drop_index("ix_lora_devices_user_id", table_name="lora_devices")
    with op.batch_alter_table("lora_devices") as b:
        b.drop_column("user_id")
        b.add_column(sa.Column("project_id", sa.String(36), nullable=False, server_default=""))
    op.create_index("ix_lora_devices_project_id", "lora_devices", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_lora_devices_project_id", table_name="lora_devices")
    with op.batch_alter_table("lora_devices") as b:
        b.drop_column("project_id")
        b.add_column(sa.Column("user_id", sa.String(36), nullable=False, server_default=""))
    op.create_index("ix_lora_devices_user_id", "lora_devices", ["user_id"])

    op.drop_index("ix_alert_rules_project_id", table_name="alert_rules")
    with op.batch_alter_table("alert_rules") as b:
        b.drop_column("project_id")
        b.add_column(sa.Column("user_id", sa.String(36), nullable=False, server_default=""))
    op.create_index("ix_alert_rules_user_id", "alert_rules", ["user_id"])

    op.drop_table("flow_instances")
    op.create_table(
        "flow_instances",
        sa.Column("user_id", sa.String(36), primary_key=True),
        sa.Column("container_name", sa.String(80), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="running"),
        sa.Column("last_active", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.drop_table("project_join_requests")
    op.drop_table("project_invites")
    op.drop_table("project_members")
    op.drop_index("ix_projects_tb_tenant_id", table_name="projects")
    op.drop_index("ix_projects_slug", table_name="projects")
    op.drop_table("projects")
