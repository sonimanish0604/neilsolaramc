from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class WorkOrderCreate(BaseModel):
    site_id: str
    assigned_tech_user_id: str
    scheduled_at: str  # ISO


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


class SendApprovalOut(BaseModel):
    status: str
    channel: str
    expires_at: str
    approval_token: str
    approval_url: str
    report_url: str | None = None
    delivery_status: str
    provider_message_id: str | None = None
    detail: str | None = None
