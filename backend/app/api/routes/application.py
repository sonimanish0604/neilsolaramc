from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.security import verify_firebase_jwt
from app.core.tenancy import ctx_roles, ctx_tenant_id, ctx_user_id, require_roles
from app.db.models.site import Customer, Site, SiteInverter
from app.db.models.user import User, UserRole
from app.db.session import get_admin_db, get_app_db
from app.schemas.application import (
    CustomerCreate,
    CustomerOut,
    CustomerUpdate,
    SiteCreate,
    SiteInverterCreate,
    SiteInverterOut,
    SiteInverterUpdate,
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


def _site_out(site: Site) -> SiteOut:
    return SiteOut(
        id=str(site.id),
        customer_id=str(site.customer_id),
        site_name=site.site_name,
        address=site.address,
        capacity_kw=float(site.capacity_kw) if site.capacity_kw is not None else None,
        site_latitude=float(site.site_latitude) if site.site_latitude is not None else None,
        site_longitude=float(site.site_longitude) if site.site_longitude is not None else None,
        status=site.status,
        site_supervisor_name=site.site_supervisor_name,
        site_supervisor_email=site.site_supervisor_email,
        site_supervisor_phone=site.site_supervisor_phone,
    )


def _site_inverter_out(inverter: SiteInverter) -> SiteInverterOut:
    return SiteInverterOut(
        id=str(inverter.id),
        site_id=str(inverter.site_id),
        inverter_code=inverter.inverter_code,
        display_name=inverter.display_name,
        capacity_kw=float(inverter.capacity_kw) if inverter.capacity_kw is not None else None,
        manufacturer=inverter.manufacturer,
        model=inverter.model,
        serial_number=inverter.serial_number,
        commissioned_on=inverter.commissioned_on,
        is_active=inverter.is_active,
    )


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
            site_latitude=payload.site_latitude,
            site_longitude=payload.site_longitude,
            status=payload.status,
            site_supervisor_name=payload.site_supervisor_name,
            site_supervisor_email=payload.site_supervisor_email,
            site_supervisor_phone=payload.site_supervisor_phone,
        )
        db.add(site)
        db.flush()
        return _site_out(site)


@router.get("/sites", response_model=list[SiteOut])
def list_sites(request: Request, customer_id: str | None = None):
    tenant_id, user_id = _ensure_context(request)
    require_roles("OWNER", "SUPERVISOR", "TECH", "CUSTOMER")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        stmt = select(Site)
        if customer_id:
            stmt = stmt.where(Site.customer_id == UUID(customer_id))
        rows = db.execute(stmt.order_by(Site.created_at.desc())).scalars().all()
        return [_site_out(s) for s in rows]


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
        if payload.site_latitude is not None:
            site.site_latitude = payload.site_latitude
        if payload.site_longitude is not None:
            site.site_longitude = payload.site_longitude
        if payload.status is not None:
            site.status = payload.status
        if payload.site_supervisor_name is not None:
            site.site_supervisor_name = payload.site_supervisor_name
        if payload.site_supervisor_email is not None:
            site.site_supervisor_email = payload.site_supervisor_email
        if payload.site_supervisor_phone is not None:
            site.site_supervisor_phone = payload.site_supervisor_phone
        if not (site.site_supervisor_phone or site.site_supervisor_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either site_supervisor_phone or site_supervisor_email is required",
            )

        return _site_out(site)


@router.post("/sites/{site_id}/inverters", response_model=SiteInverterOut)
def create_site_inverter(site_id: str, payload: SiteInverterCreate, request: Request):
    tenant_id, user_id = _ensure_context(request)
    require_roles("OWNER", "SUPERVISOR")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        site = db.execute(select(Site).where(Site.id == UUID(site_id))).scalar_one_or_none()
        if not site:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

        existing = db.execute(
            select(SiteInverter).where(
                SiteInverter.site_id == site.id,
                SiteInverter.inverter_code == payload.inverter_code,
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inverter code already exists for site")

        inverter = SiteInverter(
            tenant_id=tenant_id,
            site_id=site.id,
            inverter_code=payload.inverter_code,
            display_name=payload.display_name,
            capacity_kw=payload.capacity_kw,
            manufacturer=payload.manufacturer,
            model=payload.model,
            serial_number=payload.serial_number,
            commissioned_on=payload.commissioned_on,
            is_active=payload.is_active,
        )
        db.add(inverter)
        db.flush()
        return _site_inverter_out(inverter)


@router.get("/sites/{site_id}/inverters", response_model=list[SiteInverterOut])
def list_site_inverters(site_id: str, request: Request, active_only: bool = False):
    tenant_id, user_id = _ensure_context(request)
    require_roles("OWNER", "SUPERVISOR", "TECH", "CUSTOMER")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        site = db.execute(select(Site).where(Site.id == UUID(site_id))).scalar_one_or_none()
        if not site:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

        stmt = select(SiteInverter).where(SiteInverter.site_id == site.id)
        if active_only:
            stmt = stmt.where(SiteInverter.is_active.is_(True))
        rows = db.execute(stmt.order_by(SiteInverter.display_name.asc())).scalars().all()
        return [_site_inverter_out(row) for row in rows]


@router.patch("/sites/{site_id}/inverters/{inverter_id}", response_model=SiteInverterOut)
def update_site_inverter(site_id: str, inverter_id: str, payload: SiteInverterUpdate, request: Request):
    tenant_id, user_id = _ensure_context(request)
    require_roles("OWNER", "SUPERVISOR")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        inverter = db.execute(
            select(SiteInverter).where(
                SiteInverter.site_id == UUID(site_id),
                SiteInverter.id == UUID(inverter_id),
            )
        ).scalar_one_or_none()
        if not inverter:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site inverter not found")

        if payload.inverter_code is not None and payload.inverter_code != inverter.inverter_code:
            existing = db.execute(
                select(SiteInverter).where(
                    SiteInverter.site_id == inverter.site_id,
                    SiteInverter.inverter_code == payload.inverter_code,
                    SiteInverter.id != inverter.id,
                )
            ).scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inverter code already exists for site")
            inverter.inverter_code = payload.inverter_code
        if payload.display_name is not None:
            inverter.display_name = payload.display_name
        if payload.capacity_kw is not None:
            inverter.capacity_kw = payload.capacity_kw
        if payload.manufacturer is not None:
            inverter.manufacturer = payload.manufacturer
        if payload.model is not None:
            inverter.model = payload.model
        if payload.serial_number is not None:
            inverter.serial_number = payload.serial_number
        if payload.commissioned_on is not None:
            inverter.commissioned_on = payload.commissioned_on
        if payload.is_active is not None:
            inverter.is_active = payload.is_active

        return _site_inverter_out(inverter)
