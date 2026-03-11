"""add report jobs table

Revision ID: 0006_add_report_jobs
Revises: 0005_phase1c_approval_hardening
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_add_report_jobs"
down_revision = "0005_phase1c_approval_hardening"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "report_jobs",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("workorder_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("job_type", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="QUEUED"),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("generated_report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("next_retry_at", sa.String(length=40), nullable=True),
        sa.Column("started_at", sa.String(length=40), nullable=True),
        sa.Column("completed_at", sa.String(length=40), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
    )

    op.create_index("ix_report_jobs_status", "report_jobs", ["status"], unique=False)
    op.create_index("ix_report_jobs_idempotency_key", "report_jobs", ["idempotency_key"], unique=False)
    op.create_index("ix_report_jobs_next_retry_at", "report_jobs", ["next_retry_at"], unique=False)
    op.create_index("ix_report_jobs_generated_report_id", "report_jobs", ["generated_report_id"], unique=False)
    op.create_index(
        "uq_report_jobs_workorder_idempotency",
        "report_jobs",
        ["tenant_id", "workorder_id", "idempotency_key"],
        unique=True,
    )

    op.execute("ALTER TABLE report_jobs ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE report_jobs FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_report_jobs
        ON report_jobs
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
        """
    )


def downgrade():
    op.execute("DROP POLICY IF EXISTS tenant_isolation_report_jobs ON report_jobs;")
    op.execute("ALTER TABLE report_jobs DISABLE ROW LEVEL SECURITY;")

    op.drop_index("uq_report_jobs_workorder_idempotency", table_name="report_jobs")
    op.drop_index("ix_report_jobs_generated_report_id", table_name="report_jobs")
    op.drop_index("ix_report_jobs_next_retry_at", table_name="report_jobs")
    op.drop_index("ix_report_jobs_idempotency_key", table_name="report_jobs")
    op.drop_index("ix_report_jobs_status", table_name="report_jobs")
    op.drop_table("report_jobs")
