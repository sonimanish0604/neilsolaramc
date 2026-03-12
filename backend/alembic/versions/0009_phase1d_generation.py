"""phase 1d generation foundation

Revision ID: 0009_phase1d_generation
Revises: 0008_report_job_failures
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0009_phase1d_generation"
down_revision = "0008_report_job_failures"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "site_inverters",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inverter_code", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("capacity_kw", sa.Numeric(), nullable=True),
        sa.Column("manufacturer", sa.String(length=200), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("serial_number", sa.String(length=200), nullable=True),
        sa.Column("commissioned_on", sa.String(length=40), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_site_inverters_site_id", "site_inverters", ["site_id"], unique=False)
    op.create_index("ix_site_inverters_tenant_id", "site_inverters", ["tenant_id"], unique=False)

    op.add_column("inverter_readings", sa.Column("current_reading_kwh", sa.Numeric(), nullable=True))
    op.add_column("inverter_readings", sa.Column("previous_reading_kwh", sa.Numeric(), nullable=True))
    op.add_column("inverter_readings", sa.Column("generation_delta_kwh", sa.Numeric(), nullable=True))
    op.add_column(
        "inverter_readings",
        sa.Column("is_baseline", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "inverter_readings",
        sa.Column("is_anomaly", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("inverter_readings", sa.Column("anomaly_reason", sa.Text(), nullable=True))
    op.add_column("inverter_readings", sa.Column("operational_status", sa.String(length=30), nullable=True))
    op.add_column("inverter_readings", sa.Column("remarks", sa.Text(), nullable=True))
    op.add_column("inverter_readings", sa.Column("captured_at", sa.String(length=40), nullable=True))

    op.add_column("media", sa.Column("inverter_reading_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_media_inverter_reading_id", "media", ["inverter_reading_id"], unique=False)

    op.add_column("reports", sa.Column("generation_total_kwh", sa.Numeric(), nullable=True))
    op.add_column(
        "reports",
        sa.Column("generation_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.execute(
        """
        UPDATE inverter_readings
        SET
            current_reading_kwh = total_kwh,
            captured_at = COALESCE(captured_at, created_at::text),
            operational_status = COALESCE(operational_status, 'OPERATIONAL')
        WHERE total_kwh IS NOT NULL;
        """
    )
    op.execute(
        """
        UPDATE inverter_readings
        SET is_baseline = true
        WHERE current_reading_kwh IS NOT NULL
          AND previous_reading_kwh IS NULL;
        """
    )

    op.execute("ALTER TABLE site_inverters ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE site_inverters FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_site_inverters
        ON site_inverters
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
        """
    )


def downgrade():
    op.execute("DROP POLICY IF EXISTS tenant_isolation_site_inverters ON site_inverters;")
    op.execute("ALTER TABLE site_inverters DISABLE ROW LEVEL SECURITY;")

    op.drop_column("reports", "generation_snapshot_json")
    op.drop_column("reports", "generation_total_kwh")

    op.drop_index("ix_media_inverter_reading_id", table_name="media")
    op.drop_column("media", "inverter_reading_id")

    op.drop_column("inverter_readings", "captured_at")
    op.drop_column("inverter_readings", "remarks")
    op.drop_column("inverter_readings", "operational_status")
    op.drop_column("inverter_readings", "anomaly_reason")
    op.drop_column("inverter_readings", "is_anomaly")
    op.drop_column("inverter_readings", "is_baseline")
    op.drop_column("inverter_readings", "generation_delta_kwh")
    op.drop_column("inverter_readings", "previous_reading_kwh")
    op.drop_column("inverter_readings", "current_reading_kwh")

    op.drop_index("ix_site_inverters_tenant_id", table_name="site_inverters")
    op.drop_index("ix_site_inverters_site_id", table_name="site_inverters")
    op.drop_table("site_inverters")
