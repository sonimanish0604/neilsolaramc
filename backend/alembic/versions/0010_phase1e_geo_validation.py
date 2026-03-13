"""phase 1e geo validation foundation

Revision ID: 0010_phase1e_geo_validation
Revises: 0009_phase1d_generation
Create Date: 2026-03-12
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_phase1e_geo_validation"
down_revision = "0009_phase1d_generation"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sites", sa.Column("site_latitude", sa.Numeric(10, 7), nullable=True))
    op.add_column("sites", sa.Column("site_longitude", sa.Numeric(10, 7), nullable=True))

    op.add_column("inverter_readings", sa.Column("device_latitude", sa.Numeric(10, 7), nullable=True))
    op.add_column("inverter_readings", sa.Column("device_longitude", sa.Numeric(10, 7), nullable=True))
    op.add_column("inverter_readings", sa.Column("device_accuracy_meters", sa.Numeric(10, 2), nullable=True))
    op.add_column("inverter_readings", sa.Column("photo_latitude", sa.Numeric(10, 7), nullable=True))
    op.add_column("inverter_readings", sa.Column("photo_longitude", sa.Numeric(10, 7), nullable=True))
    op.add_column("inverter_readings", sa.Column("distance_to_site_meters", sa.Numeric(10, 2), nullable=True))
    op.add_column("inverter_readings", sa.Column("distance_photo_device_meters", sa.Numeric(10, 2), nullable=True))
    op.add_column("inverter_readings", sa.Column("geo_validation_status", sa.String(40), nullable=True))
    op.add_column("inverter_readings", sa.Column("geo_validation_reason", sa.Text(), nullable=True))
    op.create_index(
        "ix_inverter_readings_geo_validation_status",
        "inverter_readings",
        ["geo_validation_status"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_inverter_readings_geo_validation_status", table_name="inverter_readings")
    op.drop_column("inverter_readings", "geo_validation_reason")
    op.drop_column("inverter_readings", "geo_validation_status")
    op.drop_column("inverter_readings", "distance_photo_device_meters")
    op.drop_column("inverter_readings", "distance_to_site_meters")
    op.drop_column("inverter_readings", "photo_longitude")
    op.drop_column("inverter_readings", "photo_latitude")
    op.drop_column("inverter_readings", "device_accuracy_meters")
    op.drop_column("inverter_readings", "device_longitude")
    op.drop_column("inverter_readings", "device_latitude")

    op.drop_column("sites", "site_longitude")
    op.drop_column("sites", "site_latitude")
