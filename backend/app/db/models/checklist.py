from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TenantScopedMixin


class ChecklistTemplate(TenantScopedMixin, Base):
    __tablename__ = "checklist_templates"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ChecklistItem(TenantScopedMixin, Base):
    __tablename__ = "checklist_items"

    template_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(120), nullable=False)
    item_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    item_text: Mapped[str] = mapped_column(String(500), nullable=False)
    input_type: Mapped[str] = mapped_column(String(40), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_photo_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_photos_per_item: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    options_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

