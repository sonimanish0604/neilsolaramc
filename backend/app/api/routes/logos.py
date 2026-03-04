from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from uuid import UUID

from app.core.security import verify_firebase_jwt
from app.core.tenancy import ctx_roles, ctx_tenant_id, ctx_user_id, require_roles
from app.db.session import get_admin_db, get_app_db
from app.db.models.tenant import Tenant
from app.db.models.site import Customer
from app.db.models.user import User, UserRole
from app.schemas.logos import LogoSetIn, LogoOut

router = APIRouter(prefix="/logos", tags=["logos"])


def _load_user_and_tenant(firebase_uid: str):
    with get_admin_db() as adb:
        user = adb.execute(select(User).where(User.firebase_uid == firebase_uid)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        roles = adb.execute(select(UserRole.role).where(UserRole.user_id == user.id)).scalars().all()
        return user.tenant_id, user.id, set(roles)


@router.get("/tenant", response_model=LogoOut)
def get_tenant_logo(request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)

    require_roles("OWNER", "SUPERVISOR", "TECH", "CUSTOMER")

    # tenants table is not RLS, so use admin to read it safely
    with get_admin_db() as adb:
        t = adb.execute(select(Tenant).where(Tenant.id == tenant_id)).scalar_one_or_none()
        return LogoOut(object_path=t.logo_object_path if t else None, signed_url=None)


@router.post("/tenant", response_model=LogoOut)
def set_tenant_logo(payload: LogoSetIn, request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)

    require_roles("OWNER", "SUPERVISOR")

    with get_admin_db() as adb:
        t = adb.execute(select(Tenant).where(Tenant.id == tenant_id)).scalar_one_or_none()
        if not t:
            raise HTTPException(status_code=404, detail="Tenant not found")
        t.logo_object_path = payload.object_path
        adb.commit()
        return LogoOut(object_path=t.logo_object_path, signed_url=None)


@router.get("/customers/{customer_id}", response_model=LogoOut)
def get_customer_logo(customer_id: str, request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)

    require_roles("OWNER", "SUPERVISOR", "TECH", "CUSTOMER")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        c = db.execute(select(Customer).where(Customer.id == UUID(customer_id))).scalar_one_or_none()
        if not c:
            raise HTTPException(status_code=404, detail="Customer not found")
        return LogoOut(object_path=c.logo_object_path, signed_url=None)


@router.post("/customers/{customer_id}", response_model=LogoOut)
def set_customer_logo(customer_id: str, payload: LogoSetIn, request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)

    require_roles("OWNER", "SUPERVISOR")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        c = db.execute(select(Customer).where(Customer.id == UUID(customer_id))).scalar_one_or_none()
        if not c:
            raise HTTPException(status_code=404, detail="Customer not found")
        c.logo_object_path = payload.object_path
        return LogoOut(object_path=c.logo_object_path, signed_url=None)