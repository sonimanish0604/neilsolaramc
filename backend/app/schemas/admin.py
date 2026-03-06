from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TenantCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    plan_code: str = Field(default="TRIAL", min_length=2, max_length=50)
    status: str = Field(default="ACTIVE", min_length=2, max_length=20)


class TenantOut(BaseModel):
    id: str
    name: str
    plan_code: str
    status: str
    created_at: datetime


class UserCreateIn(BaseModel):
    tenant_id: str
    firebase_uid: str = Field(min_length=3, max_length=200)
    name: str = Field(min_length=2, max_length=200)
    email: str | None = None
    phone: str | None = Field(default=None, max_length=50)
    status: str = Field(default="ACTIVE", min_length=2, max_length=20)


class UserOut(BaseModel):
    id: str
    tenant_id: str
    firebase_uid: str
    name: str
    email: str | None
    phone: str | None
    status: str


class UserRoleAssignIn(BaseModel):
    role: str = Field(min_length=2, max_length=20)


class UserRoleOut(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    role: str
