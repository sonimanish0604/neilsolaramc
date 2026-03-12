from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class CustomerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    address: Optional[str] = None
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|INACTIVE)$")


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    address: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")


class CustomerOut(BaseModel):
    id: str
    name: str
    address: Optional[str] = None
    status: str


class SiteCreate(BaseModel):
    customer_id: str
    site_name: str = Field(min_length=2, max_length=200)
    address: Optional[str] = None
    capacity_kw: Optional[float] = Field(default=None, ge=0)
    site_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    site_longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|INACTIVE)$")
    site_supervisor_name: Optional[str] = Field(default=None, max_length=200)
    site_supervisor_email: Optional[str] = Field(default=None, max_length=200)
    site_supervisor_phone: Optional[str] = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_contact_present(self):
        if not (self.site_supervisor_phone or self.site_supervisor_email):
            raise ValueError("Either site_supervisor_phone or site_supervisor_email is required")
        if (self.site_latitude is None) != (self.site_longitude is None):
            raise ValueError("Both site_latitude and site_longitude are required when setting site coordinates")
        return self


class SiteUpdate(BaseModel):
    site_name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    address: Optional[str] = None
    capacity_kw: Optional[float] = Field(default=None, ge=0)
    site_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    site_longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    status: Optional[str] = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")
    site_supervisor_name: Optional[str] = Field(default=None, max_length=200)
    site_supervisor_email: Optional[str] = Field(default=None, max_length=200)
    site_supervisor_phone: Optional[str] = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_coordinates_pair(self):
        if (self.site_latitude is None) != (self.site_longitude is None):
            raise ValueError("Both site_latitude and site_longitude are required when setting site coordinates")
        return self


class SiteOut(BaseModel):
    id: str
    customer_id: str
    site_name: str
    address: Optional[str] = None
    capacity_kw: Optional[float] = None
    site_latitude: Optional[float] = None
    site_longitude: Optional[float] = None
    status: str
    site_supervisor_name: Optional[str] = None
    site_supervisor_email: Optional[str] = None
    site_supervisor_phone: Optional[str] = None


class SiteInverterCreate(BaseModel):
    inverter_code: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=200)
    capacity_kw: Optional[float] = Field(default=None, ge=0)
    manufacturer: Optional[str] = Field(default=None, max_length=200)
    model: Optional[str] = Field(default=None, max_length=200)
    serial_number: Optional[str] = Field(default=None, max_length=200)
    commissioned_on: Optional[str] = Field(default=None, max_length=40)
    is_active: bool = True


class SiteInverterUpdate(BaseModel):
    inverter_code: Optional[str] = Field(default=None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    capacity_kw: Optional[float] = Field(default=None, ge=0)
    manufacturer: Optional[str] = Field(default=None, max_length=200)
    model: Optional[str] = Field(default=None, max_length=200)
    serial_number: Optional[str] = Field(default=None, max_length=200)
    commissioned_on: Optional[str] = Field(default=None, max_length=40)
    is_active: Optional[bool] = None


class SiteInverterOut(BaseModel):
    id: str
    site_id: str
    inverter_code: str
    display_name: str
    capacity_kw: Optional[float] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    commissioned_on: Optional[str] = None
    is_active: bool
