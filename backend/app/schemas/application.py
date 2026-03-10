from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


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
    capacity_kw: Optional[float] = None
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|INACTIVE)$")
    site_supervisor_name: Optional[str] = Field(default=None, max_length=200)
    site_supervisor_email: Optional[str] = Field(default=None, max_length=200)
    site_supervisor_phone: Optional[str] = Field(default=None, max_length=50)


class SiteUpdate(BaseModel):
    site_name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    address: Optional[str] = None
    capacity_kw: Optional[float] = None
    status: Optional[str] = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")
    site_supervisor_name: Optional[str] = Field(default=None, max_length=200)
    site_supervisor_email: Optional[str] = Field(default=None, max_length=200)
    site_supervisor_phone: Optional[str] = Field(default=None, max_length=50)


class SiteOut(BaseModel):
    id: str
    customer_id: str
    site_name: str
    address: Optional[str] = None
    capacity_kw: Optional[float] = None
    status: str
    site_supervisor_name: Optional[str] = None
    site_supervisor_email: Optional[str] = None
    site_supervisor_phone: Optional[str] = None
