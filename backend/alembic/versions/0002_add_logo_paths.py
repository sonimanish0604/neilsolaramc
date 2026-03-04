"""add logo paths

Revision ID: 0002_add_logo_paths
Revises: 0001_init_and_rls
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_add_logo_paths"
down_revision = "0001_init_and_rls"
branch_labels = None
depends_on = None


def upgrade():
    # Control-plane: EPC logo
    op.add_column("tenants", sa.Column("logo_object_path", sa.String(length=500), nullable=True))

    # Application-plane: Customer logo (e.g., school/company)
    op.add_column("customers", sa.Column("logo_object_path", sa.String(length=500), nullable=True))

    # Optional indexes (helps searching/reporting later)
    op.create_index("ix_tenants_logo_object_path", "tenants", ["logo_object_path"], unique=False)
    op.create_index("ix_customers_logo_object_path", "customers", ["logo_object_path"], unique=False)


def downgrade():
    op.drop_index("ix_customers_logo_object_path", table_name="customers")
    op.drop_index("ix_tenants_logo_object_path", table_name="tenants")

    op.drop_column("customers", "logo_object_path")
    op.drop_column("tenants", "logo_object_path")