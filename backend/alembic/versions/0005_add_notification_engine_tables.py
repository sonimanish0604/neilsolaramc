"""add notification engine tables

Revision ID: 0005_notification_engine
Revises: 0004_checklist_templates
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_notification_engine"
down_revision = "0004_checklist_templates"
branch_labels = None
depends_on = None


TENANT_TABLES = [
    "notification_events",
    "tenant_notification_settings",
    "notification_templates",
    "notification_logs",
]


def upgrade():
    op.create_table(
        "notification_events",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
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
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.String(length=40), nullable=True),
        sa.Column("processed_at", sa.String(length=40), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.create_index("ix_notification_events_event_type", "notification_events", ["event_type"], unique=False)
    op.create_index("ix_notification_events_entity_type", "notification_events", ["entity_type"], unique=False)
    op.create_index("ix_notification_events_entity_id", "notification_events", ["entity_id"], unique=False)
    op.create_index("ix_notification_events_status", "notification_events", ["status"], unique=False)

    op.create_table(
        "tenant_notification_settings",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "channels_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "recipient_roles_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("template_key", sa.String(length=120), nullable=False),
    )
    op.create_index(
        "uq_tenant_notification_settings_event",
        "tenant_notification_settings",
        ["tenant_id", "event_type"],
        unique=True,
    )

    op.create_table(
        "notification_templates",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("template_key", sa.String(length=120), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index(
        "uq_notification_templates_key_channel",
        "notification_templates",
        ["tenant_id", "template_key", "channel"],
        unique=True,
    )

    op.create_table(
        "notification_logs",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
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
    )
    op.create_index("ix_notification_logs_event_id", "notification_logs", ["event_id"], unique=False)
    op.create_index("ix_notification_logs_channel", "notification_logs", ["channel"], unique=False)
    op.create_index("ix_notification_logs_status", "notification_logs", ["status"], unique=False)

    for table_name in TENANT_TABLES:
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
    for table_name in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table_name} ON {table_name};")
        op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;")

    op.drop_index("ix_notification_logs_status", table_name="notification_logs")
    op.drop_index("ix_notification_logs_channel", table_name="notification_logs")
    op.drop_index("ix_notification_logs_event_id", table_name="notification_logs")
    op.drop_table("notification_logs")

    op.drop_index("uq_notification_templates_key_channel", table_name="notification_templates")
    op.drop_table("notification_templates")

    op.drop_index("uq_tenant_notification_settings_event", table_name="tenant_notification_settings")
    op.drop_table("tenant_notification_settings")

    op.drop_index("ix_notification_events_status", table_name="notification_events")
    op.drop_index("ix_notification_events_entity_id", table_name="notification_events")
    op.drop_index("ix_notification_events_entity_type", table_name="notification_events")
    op.drop_index("ix_notification_events_event_type", table_name="notification_events")
    op.drop_table("notification_events")
