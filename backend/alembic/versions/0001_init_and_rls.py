"""init and rls

Revision ID: 0001_init_and_rls
Revises:
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_init_and_rls"
down_revision = None
branch_labels = None
depends_on = None


TENANT_TABLES = [
    "users",
    "user_roles",
    "customers",
    "sites",
    "work_orders",
    "checklist_responses",
    "net_meter_readings",
    "inverter_readings",
    "media",
    "signatures",
    "reports",
    "approval_events",
]


def upgrade():
    # --- core tables
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("plan_code", sa.String(length=50), nullable=False, server_default="TRIAL"),
        sa.Column("plan_limits", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    def tenant_scoped_columns():
        return [
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        ]

    op.create_table(
        "users",
        *tenant_scoped_columns(),
        sa.Column("firebase_uid", sa.String(length=200), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
    )

    op.create_table(
        "user_roles",
        *tenant_scoped_columns(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("role", sa.String(length=20), nullable=False, index=True),
    )

    op.create_table(
        "customers",
        *tenant_scoped_columns(),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
    )

    op.create_table(
        "sites",
        *tenant_scoped_columns(),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("site_name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("capacity_kw", sa.Numeric(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("site_supervisor_name", sa.String(length=200), nullable=True),
        sa.Column("site_supervisor_phone", sa.String(length=50), nullable=True),
    )

    op.create_table(
        "work_orders",
        *tenant_scoped_columns(),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("assigned_tech_user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("scheduled_at", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="SCHEDULED"),
        sa.Column("visit_status", sa.String(length=30), nullable=True),
        sa.Column("summary_notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "checklist_responses",
        *tenant_scoped_columns(),
        sa.Column("workorder_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("template_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("answers_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "net_meter_readings",
        *tenant_scoped_columns(),
        sa.Column("workorder_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("net_kwh", sa.Numeric(), nullable=False),
        sa.Column("imp_kwh", sa.Numeric(), nullable=False),
        sa.Column("exp_kwh", sa.Numeric(), nullable=False),
    )

    op.create_table(
        "inverter_readings",
        *tenant_scoped_columns(),
        sa.Column("workorder_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("inverter_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("power_kw", sa.Numeric(), nullable=True),
        sa.Column("day_kwh", sa.Numeric(), nullable=True),
        sa.Column("total_kwh", sa.Numeric(), nullable=True),
    )

    op.create_table(
        "media",
        *tenant_scoped_columns(),
        sa.Column("workorder_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("item_key", sa.String(length=100), nullable=True, index=True),
        sa.Column("media_type", sa.String(length=20), nullable=False, server_default="PHOTO"),
        sa.Column("gcs_object_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
    )

    op.create_table(
        "signatures",
        *tenant_scoped_columns(),
        sa.Column("workorder_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("signer_role", sa.String(length=30), nullable=False),
        sa.Column("signer_name", sa.String(length=200), nullable=False),
        sa.Column("signer_phone", sa.String(length=50), nullable=False),
        sa.Column("signature_gcs_object_path", sa.String(length=500), nullable=False),
        sa.Column("signed_at", sa.String(length=40), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
    )

    op.create_table(
        "reports",
        *tenant_scoped_columns(),
        sa.Column("workorder_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("report_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("pdf_gcs_object_path", sa.String(length=500), nullable=False),
        sa.Column("pdf_sha256", sa.String(length=80), nullable=False),
        sa.Column("pass_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("generated_at", sa.String(length=40), nullable=False),
        sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "approval_events",
        *tenant_scoped_columns(),
        sa.Column("workorder_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="WHATSAPP"),
        sa.Column("token", sa.String(length=200), nullable=False, unique=True, index=True),
        sa.Column("expires_at", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="SENT"),
    )

    # --- RLS policies for tenant tables
    for t in TENANT_TABLES:
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_{t}
            ON {t}
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
            """
        )


def downgrade():
    for t in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{t} ON {t};")
        op.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY;")

    op.drop_table("approval_events")
    op.drop_table("reports")
    op.drop_table("signatures")
    op.drop_table("media")
    op.drop_table("inverter_readings")
    op.drop_table("net_meter_readings")
    op.drop_table("checklist_responses")
    op.drop_table("work_orders")
    op.drop_table("sites")
    op.drop_table("customers")
    op.drop_table("user_roles")
    op.drop_table("users")
    op.drop_table("tenants")

    -- Create roles (choose strong passwords, store in Secret Manager)
CREATE ROLE neilsolar_app LOGIN PASSWORD '...';
CREATE ROLE neilsolar_admin LOGIN PASSWORD '...';

-- Admin can bypass RLS:
ALTER ROLE neilsolar_admin BYPASSRLS;

-- Grant schema usage (adjust schema if needed)
GRANT CONNECT ON DATABASE yourdb TO neilsolar_app, neilsolar_admin;
GRANT USAGE ON SCHEMA public TO neilsolar_app, neilsolar_admin;

-- Table privileges (after migrations)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO neilsolar_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO neilsolar_admin;

-- Sequences (if any)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO neilsolar_app, neilsolar_admin;