from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.security import verify_firebase_jwt
from app.core.tenancy import ctx_roles, ctx_tenant_id, ctx_user_id, require_roles
from app.db.models.site import Customer, Site
from app.db.models.user import User, UserRole
from app.db.session import get_admin_db, get_app_db
from app.schemas.application import (
    CustomerCreate,
    CustomerOut,
    CustomerUpdate,
    SiteCreate,
    SiteOut,
    SiteUpdate,
)

router = APIRouter(tags=["application"])


def _load_user_and_tenant(firebase_uid: str):
    with get_admin_db() as adb:
        user = adb.execute(select(User).where(User.firebase_uid == firebase_uid)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        roles = adb.execute(select(UserRole.role).where(UserRole.user_id == user.id)).scalars().all()
        return user.tenant_id, user.id, set(roles)


def _ensure_context(request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)
    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)
    return tenant_id, user_id


@router.post("/customers", response_model=CustomerOut)
def create_customer(payload: CustomerCreate, request: Request):
    tenant_id, user_id = _ensure_context(request)
    require_roles("OWNER", "SUPERVISOR")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        existing = db.execute(select(Customer).where(Customer.name == payload.name)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Customer already exists")

        customer = Customer(
            tenant_id=tenant_id,
            name=payload.name,
            address=payload.address,
            status=payload.status,
        )
        db.add(customer)
        db.flush()
        return CustomerOut(
            id=str(customer.id),
            name=customer.name,
            address=customer.address,
            status=customer.status,
        )


@router.get("/customers", response_model=list[CustomerOut])
def list_customers(request: Request):
    tenant_id, user_id = _ensure_context(request)
    require_roles("OWNER", "SUPERVISOR", "TECH", "CUSTOMER")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        rows = db.execute(select(Customer).order_by(Customer.created_at.desc())).scalars().all()
        return [CustomerOut(id=str(c.id), name=c.name, address=c.address, status=c.status) for c in rows]


@router.patch("/customers/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: str, payload: CustomerUpdate, request: Request):
    tenant_id, user_id = _ensure_context(request)
    require_roles("OWNER", "SUPERVISOR")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        customer = db.execute(select(Customer).where(Customer.id == UUID(customer_id))).scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

        if payload.name is not None and payload.name != customer.name:
            existing = db.execute(select(Customer).where(Customer.name == payload.name)).scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Customer already exists")
            customer.name = payload.name
        if payload.address is not None:
            customer.address = payload.address
        if payload.status is not None:
            customer.status = payload.status

        return CustomerOut(
            id=str(customer.id),
            name=customer.name,
            address=customer.address,
            status=customer.status,
        )


@router.post("/sites", response_model=SiteOut)
def create_site(payload: SiteCreate, request: Request):
    tenant_id, user_id = _ensure_context(request)
    require_roles("OWNER", "SUPERVISOR")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        customer = db.execute(select(Customer).where(Customer.id == UUID(payload.customer_id))).scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

        existing = db.execute(
            select(Site).where(Site.customer_id == customer.id, Site.site_name == payload.site_name)
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Site already exists")

        site = Site(
            tenant_id=tenant_id,
            customer_id=customer.id,
            site_name=payload.site_name,
            address=payload.address,
            capacity_kw=payload.capacity_kw,
            status=payload.status,
            site_supervisor_name=payload.site_supervisor_name,
            site_supervisor_phone=payload.site_supervisor_phone,
        )
        db.add(site)
        db.flush()
        return SiteOut(
            id=str(site.id),
            customer_id=str(site.customer_id),
            site_name=site.site_name,
            address=site.address,
            capacity_kw=float(site.capacity_kw) if site.capacity_kw is not None else None,
            status=site.status,
            site_supervisor_name=site.site_supervisor_name,
            site_supervisor_phone=site.site_supervisor_phone,
        )


@router.get("/sites", response_model=list[SiteOut])
def list_sites(request: Request, customer_id: str | None = None):
    tenant_id, user_id = _ensure_context(request)
    require_roles("OWNER", "SUPERVISOR", "TECH", "CUSTOMER")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        stmt = select(Site)
        if customer_id:
            stmt = stmt.where(Site.customer_id == UUID(customer_id))
        rows = db.execute(stmt.order_by(Site.created_at.desc())).scalars().all()
        return [
            SiteOut(
                id=str(s.id),
                customer_id=str(s.customer_id),
                site_name=s.site_name,
                address=s.address,
                capacity_kw=float(s.capacity_kw) if s.capacity_kw is not None else None,
                status=s.status,
                site_supervisor_name=s.site_supervisor_name,
                site_supervisor_phone=s.site_supervisor_phone,
            )
            for s in rows
        ]


@router.patch("/sites/{site_id}", response_model=SiteOut)
def update_site(site_id: str, payload: SiteUpdate, request: Request):
    tenant_id, user_id = _ensure_context(request)
    require_roles("OWNER", "SUPERVISOR")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        site = db.execute(select(Site).where(Site.id == UUID(site_id))).scalar_one_or_none()
        if not site:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

        if payload.site_name is not None and payload.site_name != site.site_name:
            existing = db.execute(
                select(Site).where(Site.customer_id == site.customer_id, Site.site_name == payload.site_name)
            ).scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Site already exists")
            site.site_name = payload.site_name
        if payload.address is not None:
            site.address = payload.address
        if payload.capacity_kw is not None:
            site.capacity_kw = payload.capacity_kw
        if payload.status is not None:
            site.status = payload.status
        if payload.site_supervisor_name is not None:
            site.site_supervisor_name = payload.site_supervisor_name
        if payload.site_supervisor_phone is not None:
            site.site_supervisor_phone = payload.site_supervisor_phone

        return SiteOut(
            id=str(site.id),
            customer_id=str(site.customer_id),
            site_name=site.site_name,
            address=site.address,
            capacity_kw=float(site.capacity_kw) if site.capacity_kw is not None else None,
            status=site.status,
            site_supervisor_name=site.site_supervisor_name,
            site_supervisor_phone=site.site_supervisor_phone,
        )

