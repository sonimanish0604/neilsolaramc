from sqlalchemy import Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TenantScopedMixin


class WorkOrder(TenantScopedMixin, Base):
    __tablename__ = "work_orders"

    site_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    assigned_tech_user_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    scheduled_at: Mapped[str] = mapped_column(String(40), nullable=False)  # store ISO string for simplicity MVP
    status: Mapped[str] = mapped_column(String(30), default="SCHEDULED", nullable=False, index=True)

    visit_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    summary_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ChecklistResponse(TenantScopedMixin, Base):
    __tablename__ = "checklist_responses"

    workorder_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    template_version: Mapped[int] = mapped_column(nullable=False, default=1)
    answers_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class NetMeterReading(TenantScopedMixin, Base):
    __tablename__ = "net_meter_readings"

    workorder_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    net_kwh: Mapped[float] = mapped_column(Numeric, nullable=False)
    imp_kwh: Mapped[float] = mapped_column(Numeric, nullable=False)
    exp_kwh: Mapped[float] = mapped_column(Numeric, nullable=False)


class InverterReading(TenantScopedMixin, Base):
    __tablename__ = "inverter_readings"

    workorder_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    inverter_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    power_kw: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    day_kwh: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    total_kwh: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    current_reading_kwh: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    previous_reading_kwh: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    generation_delta_kwh: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    is_baseline: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_anomaly: Mapped[bool] = mapped_column(nullable=False, default=False)
    anomaly_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    device_longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    device_accuracy_meters: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    photo_latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    photo_longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    distance_to_site_meters: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    distance_photo_device_meters: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    geo_validation_status: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    geo_validation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    operational_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Media(TenantScopedMixin, Base):
    __tablename__ = "media"

    workorder_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    inverter_reading_id: Mapped[PGUUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    item_key: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    media_type: Mapped[str] = mapped_column(String(20), default="PHOTO", nullable=False)
    gcs_object_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)


class Signature(TenantScopedMixin, Base):
    __tablename__ = "signatures"

    workorder_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    signer_role: Mapped[str] = mapped_column(String(30), nullable=False)  # TECH / CUSTOMER_SUPERVISOR
    signer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    signer_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    signature_gcs_object_path: Mapped[str] = mapped_column(String(500), nullable=False)
    signed_at: Mapped[str] = mapped_column(String(40), nullable=False)  # ISO string
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)


class Report(TenantScopedMixin, Base):
    __tablename__ = "reports"

    workorder_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    report_version: Mapped[int] = mapped_column(nullable=False, default=1)
    pdf_gcs_object_path: Mapped[str] = mapped_column(String(500), nullable=False)
    pdf_sha256: Mapped[str] = mapped_column(String(80), nullable=False)
    pass_count: Mapped[int] = mapped_column(nullable=False, default=0)
    fail_count: Mapped[int] = mapped_column(nullable=False, default=0)
    generation_total_kwh: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    generation_snapshot_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generated_at: Mapped[str] = mapped_column(String(40), nullable=False)
    is_final: Mapped[bool] = mapped_column(nullable=False, default=False)


class ReportJob(TenantScopedMixin, Base):
    __tablename__ = "report_jobs"

    workorder_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="QUEUED", index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    generated_report_id: Mapped[PGUUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(nullable=False, default=3)
    simulate_failures_remaining: Mapped[int] = mapped_column(nullable=False, default=0)
    next_retry_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    started_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class ApprovalEvent(TenantScopedMixin, Base):
    __tablename__ = "approval_events"

    workorder_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), default="WHATSAPP", nullable=False)
    token: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    expires_at: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="QUEUED", nullable=False, index=True)
    recipient: Mapped[str | None] = mapped_column(String(200), nullable=True)
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)
    next_retry_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    opened_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    signed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reminder_count: Mapped[int] = mapped_column(nullable=False, default=0)
    last_reminder_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    superseded_by_event_id: Mapped[PGUUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
