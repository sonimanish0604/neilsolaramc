"""add correlation ids for report jobs and approval events

Revision ID: 0007_add_correlation_ids
Revises: 0006_add_report_jobs
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_add_correlation_ids"
down_revision = "0006_add_report_jobs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("approval_events", sa.Column("correlation_id", sa.String(length=100), nullable=True))
    op.add_column("report_jobs", sa.Column("correlation_id", sa.String(length=100), nullable=True))

    op.create_index("ix_approval_events_correlation_id", "approval_events", ["correlation_id"], unique=False)
    op.create_index("ix_report_jobs_correlation_id", "report_jobs", ["correlation_id"], unique=False)


def downgrade():
    op.drop_index("ix_report_jobs_correlation_id", table_name="report_jobs")
    op.drop_index("ix_approval_events_correlation_id", table_name="approval_events")

    op.drop_column("report_jobs", "correlation_id")
    op.drop_column("approval_events", "correlation_id")
