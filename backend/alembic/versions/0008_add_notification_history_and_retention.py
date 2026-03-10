"""add notification history and retention policy tables

Revision ID: 0008_notification_history_retention
Revises: 0007_site_supervisor_email
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0008_notif_history_retention"
down_revision = "0007_site_supervisor_email"
branch_labels = None
depends_on = None


RLS_TABLES = [
    "notification_events_history",
    "notification_logs_history",
    "notification_delivery_jobs_history",
    "tenant_data_retention_policy",
]


def upgrade():
    op.create_table(
        "notification_events_history",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.String(length=40), nullable=True),
        sa.Column("processed_at", sa.String(length=40), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_notification_events_history_tenant_id", "notification_events_history", ["tenant_id"], unique=False)
    op.create_index("ix_notification_events_history_event_type", "notification_events_history", ["event_type"], unique=False)
    op.create_index("ix_notification_events_history_entity_type", "notification_events_history", ["entity_type"], unique=False)
    op.create_index("ix_notification_events_history_entity_id", "notification_events_history", ["entity_id"], unique=False)
    op.create_index("ix_notification_events_history_status", "notification_events_history", ["status"], unique=False)
    op.create_index("ix_notification_events_history_archived_at", "notification_events_history", ["archived_at"], unique=False)

    op.create_table(
        "notification_logs_history",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("recipient", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=True),
        sa.Column("provider_message_id", sa.String(length=200), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.String(length=40), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_notification_logs_history_tenant_id", "notification_logs_history", ["tenant_id"], unique=False)
    op.create_index("ix_notification_logs_history_event_id", "notification_logs_history", ["event_id"], unique=False)
    op.create_index("ix_notification_logs_history_channel", "notification_logs_history", ["channel"], unique=False)
    op.create_index("ix_notification_logs_history_status", "notification_logs_history", ["status"], unique=False)
    op.create_index("ix_notification_logs_history_archived_at", "notification_logs_history", ["archived_at"], unique=False)

    op.create_table(
        "notification_delivery_jobs_history",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notification_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("recipient", sa.String(length=200), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.String(length=40), nullable=True),
        sa.Column("processed_at", sa.String(length=40), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_notification_delivery_jobs_history_tenant_id",
        "notification_delivery_jobs_history",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_notification_delivery_jobs_history_event_id",
        "notification_delivery_jobs_history",
        ["notification_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_notification_delivery_jobs_history_channel",
        "notification_delivery_jobs_history",
        ["channel"],
        unique=False,
    )
    op.create_index(
        "ix_notification_delivery_jobs_history_status",
        "notification_delivery_jobs_history",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_notification_delivery_jobs_history_archived_at",
        "notification_delivery_jobs_history",
        ["archived_at"],
        unique=False,
    )

    op.create_table(
        "tenant_data_retention_policy",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("active_retention_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("notification_history_retention_days", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("dead_letter_retention_days", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("purge_after_deactivation_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("archive_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("purge_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_tenant_data_retention_policy_archive_enabled",
        "tenant_data_retention_policy",
        ["archive_enabled"],
        unique=False,
    )
    op.create_index(
        "ix_tenant_data_retention_policy_purge_enabled",
        "tenant_data_retention_policy",
        ["purge_enabled"],
        unique=False,
    )

    for table_name in RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_{table_name}
            ON {table_name}
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
            """
        )


def downgrade():
    for table_name in RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table_name} ON {table_name};")
        op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;")

    op.drop_index("ix_tenant_data_retention_policy_purge_enabled", table_name="tenant_data_retention_policy")
    op.drop_index("ix_tenant_data_retention_policy_archive_enabled", table_name="tenant_data_retention_policy")
    op.drop_table("tenant_data_retention_policy")

    op.drop_index("ix_notification_delivery_jobs_history_archived_at", table_name="notification_delivery_jobs_history")
    op.drop_index("ix_notification_delivery_jobs_history_status", table_name="notification_delivery_jobs_history")
    op.drop_index("ix_notification_delivery_jobs_history_channel", table_name="notification_delivery_jobs_history")
    op.drop_index("ix_notification_delivery_jobs_history_event_id", table_name="notification_delivery_jobs_history")
    op.drop_index("ix_notification_delivery_jobs_history_tenant_id", table_name="notification_delivery_jobs_history")
    op.drop_table("notification_delivery_jobs_history")

    op.drop_index("ix_notification_logs_history_archived_at", table_name="notification_logs_history")
    op.drop_index("ix_notification_logs_history_status", table_name="notification_logs_history")
    op.drop_index("ix_notification_logs_history_channel", table_name="notification_logs_history")
    op.drop_index("ix_notification_logs_history_event_id", table_name="notification_logs_history")
    op.drop_index("ix_notification_logs_history_tenant_id", table_name="notification_logs_history")
    op.drop_table("notification_logs_history")

    op.drop_index("ix_notification_events_history_archived_at", table_name="notification_events_history")
    op.drop_index("ix_notification_events_history_status", table_name="notification_events_history")
    op.drop_index("ix_notification_events_history_entity_id", table_name="notification_events_history")
    op.drop_index("ix_notification_events_history_entity_type", table_name="notification_events_history")
    op.drop_index("ix_notification_events_history_event_type", table_name="notification_events_history")
    op.drop_index("ix_notification_events_history_tenant_id", table_name="notification_events_history")
    op.drop_table("notification_events_history")
