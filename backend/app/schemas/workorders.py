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
    operational_status: Optional[str] = Field(
        default=None,
        pattern="^(OPERATIONAL|OFFLINE|FAULT|UNAVAILABLE)$",
    )
    remarks: Optional[str] = None


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
        inverter_ids = [reading.inverter_id for reading in self.inverter_readings]
        if len(set(inverter_ids)) != len(inverter_ids):
            raise ValueError("Duplicate inverter_id entries are not allowed")
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


class WorkOrderConfiguredInverterOut(BaseModel):
    inverter_id: str
    inverter_code: str
    display_name: str
    capacity_kw: Optional[float] = None
    latest_accepted_reading_kwh: Optional[float] = None


class WorkOrderInverterListOut(BaseModel):
    workorder_id: str
    site_id: str
    inverters: list[WorkOrderConfiguredInverterOut]


class InverterReadingCaptureIn(BaseModel):
    inverter_id: str
    current_reading_kwh: Optional[float] = Field(default=None, ge=0)
    device_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    device_longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    device_accuracy_meters: Optional[float] = Field(default=None, ge=0)
    operational_status: str = Field(pattern="^(OPERATIONAL|OFFLINE|FAULT|UNAVAILABLE)$")
    remarks: Optional[str] = None
    photo_object_path: str
    photo_content_type: str
    photo_size_bytes: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_status_and_reading(self):
        if self.operational_status == "OPERATIONAL" and self.current_reading_kwh is None:
            raise ValueError("current_reading_kwh is required when operational_status is OPERATIONAL")
        if self.current_reading_kwh is None and not (self.remarks and self.remarks.strip()):
            raise ValueError("remarks are required when current_reading_kwh is omitted")
        if (self.device_latitude is None) != (self.device_longitude is None):
            raise ValueError("Both device_latitude and device_longitude are required when location is provided")
        if self.device_accuracy_meters is not None and (
            self.device_latitude is None or self.device_longitude is None
        ):
            raise ValueError("device_accuracy_meters requires both device_latitude and device_longitude")
        return self


class InverterReadingCaptureOut(BaseModel):
    reading_id: str
    inverter_id: str
    inverter_code: str
    display_name: str
    previous_reading_kwh: Optional[float] = None
    current_reading_kwh: Optional[float] = None
    generation_delta_kwh: Optional[float] = None
    is_baseline: bool
    is_anomaly: bool
    anomaly_reason: Optional[str] = None
    device_latitude: Optional[float] = None
    device_longitude: Optional[float] = None
    device_accuracy_meters: Optional[float] = None
    distance_to_site_meters: Optional[float] = None
    geo_validation_status: Optional[str] = None
    geo_validation_reason: Optional[str] = None
    operational_status: Optional[str] = None
    remarks: Optional[str] = None
    photo_object_path: str


class ReportDataInverterOut(BaseModel):
    inverter_id: str
    inverter_code: str
    display_name: str
    previous_reading_kwh: Optional[float] = None
    current_reading_kwh: Optional[float] = None
    generation_delta_kwh: Optional[float] = None
    is_baseline: bool
    is_anomaly: bool
    anomaly_reason: Optional[str] = None
    operational_status: Optional[str] = None
    remarks: Optional[str] = None
    photo_object_path: Optional[str] = None


class WorkOrderReportDataOut(BaseModel):
    workorder_id: str
    site_id: str
    generation_total_kwh: float
    baseline_inverter_count: int
    anomaly_count: int
    inverters: list[ReportDataInverterOut]
