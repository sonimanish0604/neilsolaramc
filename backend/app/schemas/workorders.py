from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


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
    size_bytes: int


class TechSignatureIn(BaseModel):
    signer_name: str
    signer_phone: str
    signature_object_path: str


class WorkOrderSubmit(BaseModel):
    visit_status: str = Field(pattern="^(SATISFACTORY|NEEDS_ATTENTION|CRITICAL)$")
    summary_notes: Optional[str] = None
    inverter_readings: List[InverterReadingIn] = Field(default_factory=list)
    net_meter: NetMeterIn
    checklist_answers: Dict[str, Any]
    media: List[MediaIn] = Field(default_factory=list)
    tech_signature: TechSignatureIn