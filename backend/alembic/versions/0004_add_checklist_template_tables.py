"""add checklist template tables

Revision ID: 0004_checklist_templates
Revises: 0003_add_audit_log
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_checklist_templates"
down_revision = "0003_add_audit_log"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "checklist_templates",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.create_table(
        "checklist_items",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("section", sa.String(length=120), nullable=False),
        sa.Column("item_key", sa.String(length=120), nullable=False),
        sa.Column("item_text", sa.String(length=500), nullable=False),
        sa.Column("input_type", sa.String(length=40), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_photo_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("max_photos_per_item", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "options_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.create_index("ix_checklist_items_item_key", "checklist_items", ["item_key"], unique=False)
    op.create_index(
        "uq_checklist_item_key_per_template",
        "checklist_items",
        ["tenant_id", "template_id", "item_key"],
        unique=True,
    )
    op.create_index(
        "uq_checklist_template_version",
        "checklist_templates",
        ["tenant_id", "title", "version"],
        unique=True,
    )

    for table_name in ("checklist_templates", "checklist_items"):
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
    for table_name in ("checklist_templates", "checklist_items"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table_name} ON {table_name};")
        op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;")

    op.drop_index("uq_checklist_template_version", table_name="checklist_templates")
    op.drop_index("uq_checklist_item_key_per_template", table_name="checklist_items")
    op.drop_index("ix_checklist_items_item_key", table_name="checklist_items")
    op.drop_table("checklist_items")
    op.drop_table("checklist_templates")
