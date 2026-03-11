from sqlalchemy import String, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TenantScopedMixin


class Customer(TenantScopedMixin, Base):
    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    logo_object_path: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Site(TenantScopedMixin, Base):
    __tablename__ = "sites"

    customer_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    site_name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    capacity_kw: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)

    site_supervisor_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    site_supervisor_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    site_supervisor_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
