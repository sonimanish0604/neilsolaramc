from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class WorkOrderCreate(BaseModel):
    site_id: str
    assigned_tech_user_id: str
    scheduled_at: str


class WorkOrderOut(BaseModel):
    id: str
    site_id: str
    assigned_tech_user_id: str
    scheduled_at: str
    status: str
    visit_status: Optional[str] = None
    summary_notes: Optional[str] = None


class InverterReadingIn(BaseModel):
    inverter_id: str
    power_kw: Optional[float] = None
    day_kwh: Optional[float] = None
    total_kwh: Optional[float] = None


class NetMeterIn(BaseModel):
    net_kwh: float
    imp_kwh: float
    exp_kwh: float


class MediaIn(BaseModel):
    item_key: Optional[str] = None
    object_path: str
    content_type: str
    size_bytes: int = Field(gt=0)


class TechSignatureIn(BaseModel):
    signer_name: str
    signer_phone: str
    signature_object_path: str

    @model_validator(mode="after")
    def validate_png_signature(self):
        if not self.signature_object_path.lower().endswith(".png"):
            raise ValueError("signature_object_path must be a .png")
        return self


class WorkOrderSubmit(BaseModel):
    visit_status: str = Field(pattern="^(SATISFACTORY|NEEDS_ATTENTION|CRITICAL)$")
    summary_notes: Optional[str] = None
    inverter_readings: List[InverterReadingIn] = Field(default_factory=list)
    net_meter: NetMeterIn
    checklist_answers: Dict[str, Any]
    media: List[MediaIn] = Field(default_factory=list)
    tech_signature: TechSignatureIn

    @model_validator(mode="after")
    def validate_media_rules(self):
        if len(self.media) > 20:
            raise ValueError("A maximum of 20 photos is allowed per visit")
        if not any(m.item_key == "net_meter_readings" for m in self.media):
            raise ValueError("At least one net_meter_readings photo is required")
        return self


class WorkOrderStatusUpdate(BaseModel):
    status: str = Field(pattern="^(IN_PROGRESS|CLOSED)$")


class SendApprovalIn(BaseModel):
    channel: str = Field(default="WHATSAPP", pattern="^(WHATSAPP|EMAIL)$")


class ApprovalSendOut(BaseModel):
    event_id: str
    correlation_id: str | None
    workorder_id: str
    channel: str
    recipient: str | None
    status: str
    token_expires_at: str
    approval_link: str
    attempt_count: int
    next_retry_at: str | None
    approval_token: str | None = None
    approval_url: str | None = None
    report_url: str | None = None
    delivery_status: str | None = None
    provider_message_id: str | None = None
    detail: str | None = None


class ApprovalResendIn(BaseModel):
    mode: str = Field(default="NEW_TOKEN", pattern="^(NEW_TOKEN|EXTEND)$")


class ApprovalReminderRunOut(BaseModel):
    scanned: int
    reminders_sent: int
    skipped: int


class ReportJobCreateIn(BaseModel):
    is_final: bool = False
    idempotency_key: str | None = None
    simulate_failures: int = Field(default=0, ge=0, le=3)


class ReportJobOut(BaseModel):
    job_id: str
    correlation_id: str | None
    workorder_id: str
    job_type: str
    status: str
    attempt_count: int
    max_attempts: int
    next_retry_at: str | None
    last_error: str | None
    generated_report_id: str | None
    report_pdf_url: str | None


class GenerateReportSyncOut(BaseModel):
    status: str
    job: ReportJobOut
