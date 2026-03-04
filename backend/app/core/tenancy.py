from __future__ import annotations

from contextvars import ContextVar
from typing import Optional, Set
from uuid import UUID

from fastapi import HTTPException, status

ctx_tenant_id: ContextVar[Optional[UUID]] = ContextVar("tenant_id", default=None)
ctx_user_id: ContextVar[Optional[UUID]] = ContextVar("user_id", default=None)
ctx_roles: ContextVar[Set[str]] = ContextVar("roles", default=set())


def require_roles(*allowed: str) -> None:
    roles = ctx_roles.get()
    if not roles.intersection(set(allowed)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def get_tenant_id() -> UUID:
    tenant_id = ctx_tenant_id.get()
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant context missing")
    return tenant_id