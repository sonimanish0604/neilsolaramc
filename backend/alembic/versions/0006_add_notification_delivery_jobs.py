"""add notification delivery jobs

Revision ID: 0006_notification_delivery_jobs
Revises: 0005_notification_engine
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_notification_delivery_jobs"
down_revision = "0005_notification_engine"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification_delivery_jobs",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notification_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("recipient", sa.String(length=200), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.String(length=40), nullable=True),
        sa.Column("processed_at", sa.String(length=40), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_notification_delivery_jobs_event_id",
        "notification_delivery_jobs",
        ["notification_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_notification_delivery_jobs_channel",
        "notification_delivery_jobs",
        ["channel"],
        unique=False,
    )
    op.create_index(
        "ix_notification_delivery_jobs_status",
        "notification_delivery_jobs",
        ["status"],
        unique=False,
    )

    op.execute("ALTER TABLE notification_delivery_jobs ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE notification_delivery_jobs FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_notification_delivery_jobs
        ON notification_delivery_jobs
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
        """
    )


def downgrade():
    op.execute(
        "DROP POLICY IF EXISTS tenant_isolation_notification_delivery_jobs ON notification_delivery_jobs;"
    )
    op.execute("ALTER TABLE notification_delivery_jobs DISABLE ROW LEVEL SECURITY;")

    op.drop_index("ix_notification_delivery_jobs_status", table_name="notification_delivery_jobs")
    op.drop_index("ix_notification_delivery_jobs_channel", table_name="notification_delivery_jobs")
    op.drop_index("ix_notification_delivery_jobs_event_id", table_name="notification_delivery_jobs")
    op.drop_table("notification_delivery_jobs")
