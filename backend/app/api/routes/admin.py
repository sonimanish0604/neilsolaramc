from __future__ import annotations

from contextlib import contextmanager
from typing import Generator
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.audit_log import AuditLog
from app.db.models.tenant import Tenant
from app.db.models.user import User, UserRole
from app.db.session import get_admin_db
from app.schemas.admin import (
    TenantCreateIn,
    TenantOut,
    UserCreateIn,
    UserOut,
    UserRoleAssignIn,
    UserRoleOut,
)

router = APIRouter(prefix="/admin", tags=["admin"])

ALLOWED_ROLES = {"OWNER", "SUPERVISOR", "TECH", "CUSTOMER"}


@contextmanager
def _admin_session_ctx() -> Generator[Session, None, None]:
    with get_admin_db() as db:
        yield db


def get_admin_session() -> Generator[Session, None, None]:
    with _admin_session_ctx() as db:
        yield db


def require_admin_key(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    expected = settings.bootstrap_admin_key
    if not expected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin API key not configured")
    if x_admin_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin key")


def _get_tenant_by_name(db: Session, tenant_name: str) -> Tenant | None:
    return db.execute(select(Tenant).where(Tenant.name == tenant_name)).scalar_one_or_none()


def _create_tenant(db: Session, payload: TenantCreateIn) -> Tenant:
    tenant = Tenant(name=payload.name, plan_code=payload.plan_code, status=payload.status)
    db.add(tenant)
    db.flush()
    db.refresh(tenant)
    return tenant


def _get_user_by_firebase_uid(db: Session, firebase_uid: str) -> User | None:
    return db.execute(select(User).where(User.firebase_uid == firebase_uid)).scalar_one_or_none()


def _create_user(db: Session, payload: UserCreateIn) -> User:
    user = User(
        tenant_id=UUID(payload.tenant_id),
        firebase_uid=payload.firebase_uid,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        status=payload.status,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


def _get_user_by_id(db: Session, user_id: UUID) -> User | None:
    return db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()


def _get_user_role(db: Session, user_id: UUID, role: str) -> UserRole | None:
    return db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role == role)
    ).scalar_one_or_none()


def _create_user_role(db: Session, tenant_id: UUID, user_id: UUID, role: str) -> UserRole:
    user_role = UserRole(tenant_id=tenant_id, user_id=user_id, role=role)
    db.add(user_role)
    db.flush()
    db.refresh(user_role)
    return user_role


def _write_audit_log(
    db: Session,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str | None,
    tenant_id: UUID | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata or {},
        )
    )


@router.post("/tenants", response_model=TenantOut, dependencies=[Depends(require_admin_key)])
def create_tenant(payload: TenantCreateIn, db: Session = Depends(get_admin_session)):
    if _get_tenant_by_name(db, payload.name):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant already exists")

    tenant = _create_tenant(db, payload)
    _write_audit_log(
        db,
        actor="admin_api",
        action="TENANT_CREATED",
        entity_type="tenant",
        entity_id=str(tenant.id),
        tenant_id=tenant.id,
        metadata={"name": tenant.name},
    )
    db.commit()
    return TenantOut(
        id=str(tenant.id),
        name=tenant.name,
        plan_code=tenant.plan_code,
        status=tenant.status,
        created_at=tenant.created_at,
    )


@router.post("/users", response_model=UserOut, dependencies=[Depends(require_admin_key)])
def create_user(payload: UserCreateIn, db: Session = Depends(get_admin_session)):
    if _get_user_by_firebase_uid(db, payload.firebase_uid):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="firebase_uid already exists")

    user = _create_user(db, payload)
    _write_audit_log(
        db,
        actor="admin_api",
        action="USER_CREATED",
        entity_type="user",
        entity_id=str(user.id),
        tenant_id=user.tenant_id,
        metadata={"firebase_uid": user.firebase_uid, "name": user.name},
    )
    db.commit()
    return UserOut(
        id=str(user.id),
        tenant_id=str(user.tenant_id),
        firebase_uid=user.firebase_uid,
        name=user.name,
        email=user.email,
        phone=user.phone,
        status=user.status,
    )


@router.post("/users/{user_id}/roles", response_model=UserRoleOut, dependencies=[Depends(require_admin_key)])
def assign_user_role(user_id: str, payload: UserRoleAssignIn, db: Session = Depends(get_admin_session)):
    role = payload.role.upper()
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    user_uuid = UUID(user_id)
    user = _get_user_by_id(db, user_uuid)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if _get_user_role(db, user_uuid, role):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role already assigned")

    user_role = _create_user_role(db, tenant_id=user.tenant_id, user_id=user_uuid, role=role)
    _write_audit_log(
        db,
        actor="admin_api",
        action="ROLE_ASSIGNED",
        entity_type="user_role",
        entity_id=str(user_role.id),
        tenant_id=user.tenant_id,
        metadata={"user_id": str(user_uuid), "role": role},
    )
    db.commit()
    return UserRoleOut(
        id=str(user_role.id),
        tenant_id=str(user_role.tenant_id),
        user_id=str(user_role.user_id),
        role=user_role.role,
    )

