"""add simulated failure control to report jobs

Revision ID: 0008_report_jobs_simulated_failures
Revises: 0007_add_correlation_ids
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_report_jobs_simulated_failures"
down_revision = "0007_add_correlation_ids"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "report_jobs",
        sa.Column("simulate_failures_remaining", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_column("report_jobs", "simulate_failures_remaining")
