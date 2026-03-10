"""add site supervisor email

Revision ID: 0007_site_supervisor_email
Revises: 0006_notification_delivery_jobs
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_site_supervisor_email"
down_revision = "0006_notification_delivery_jobs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sites", sa.Column("site_supervisor_email", sa.String(length=200), nullable=True))
    op.create_index("ix_sites_site_supervisor_email", "sites", ["site_supervisor_email"], unique=False)


def downgrade():
    op.drop_index("ix_sites_site_supervisor_email", table_name="sites")
    op.drop_column("sites", "site_supervisor_email")
