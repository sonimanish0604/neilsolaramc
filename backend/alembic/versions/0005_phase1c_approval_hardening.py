"""phase 1c approval hardening

Revision ID: 0005_phase1c_approval_hardening
Revises: 0004_checklist_templates
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_phase1c_approval_hardening"
down_revision = "0004_checklist_templates"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sites", sa.Column("site_supervisor_email", sa.String(length=200), nullable=True))

    op.add_column(
        "approval_events",
        sa.Column("recipient", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "approval_events",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "approval_events",
        sa.Column("next_retry_at", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "approval_events",
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "approval_events",
        sa.Column("sent_at", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "approval_events",
        sa.Column("opened_at", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "approval_events",
        sa.Column("signed_at", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "approval_events",
        sa.Column("reminder_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "approval_events",
        sa.Column("last_reminder_at", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "approval_events",
        sa.Column("superseded_by_event_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.execute("UPDATE approval_events SET status = 'QUEUED' WHERE status IS NULL;")

    op.create_index(
        "ix_approval_events_next_retry_at",
        "approval_events",
        ["next_retry_at"],
        unique=False,
    )
    op.create_index(
        "ix_approval_events_superseded_by_event_id",
        "approval_events",
        ["superseded_by_event_id"],
        unique=False,
    )

    op.alter_column(
        "approval_events",
        "status",
        existing_type=sa.String(length=20),
        server_default="QUEUED",
        existing_nullable=False,
    )


def downgrade():
    op.alter_column(
        "approval_events",
        "status",
        existing_type=sa.String(length=20),
        server_default="SENT",
        existing_nullable=False,
    )

    op.drop_index("ix_approval_events_superseded_by_event_id", table_name="approval_events")
    op.drop_index("ix_approval_events_next_retry_at", table_name="approval_events")

    op.drop_column("approval_events", "superseded_by_event_id")
    op.drop_column("approval_events", "last_reminder_at")
    op.drop_column("approval_events", "reminder_count")
    op.drop_column("approval_events", "signed_at")
    op.drop_column("approval_events", "opened_at")
    op.drop_column("approval_events", "sent_at")
    op.drop_column("approval_events", "last_error")
    op.drop_column("approval_events", "next_retry_at")
    op.drop_column("approval_events", "attempt_count")
    op.drop_column("approval_events", "recipient")

    op.drop_column("sites", "site_supervisor_email")
