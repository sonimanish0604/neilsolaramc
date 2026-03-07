from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import delete, select

from app.core.security import verify_firebase_jwt
from app.core.tenancy import ctx_roles, ctx_tenant_id, ctx_user_id, require_roles
from app.db.session import get_admin_db, get_app_db
from app.db.models.user import User, UserRole
from app.db.models.workorder import (
    WorkOrder, ChecklistResponse, NetMeterReading, InverterReading, Media, Signature
)
from app.schemas.workorders import WorkOrderCreate, WorkOrderOut, WorkOrderStatusUpdate, WorkOrderSubmit

router = APIRouter(prefix="/workorders", tags=["workorders"])


def _can_transition(current_status: str, next_status: str) -> bool:
    allowed = {
        "SCHEDULED": {"IN_PROGRESS"},
        "CUSTOMER_SIGNED": {"CLOSED"},
    }
    return next_status in allowed.get(current_status, set())


def _load_user_and_tenant(firebase_uid: str):
    """
    Uses ADMIN DB (BYPASSRLS) to resolve firebase_uid -> (tenant_id, user_id, roles).
    """
    with get_admin_db() as adb:
        user = adb.execute(select(User).where(User.firebase_uid == firebase_uid)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        roles = adb.execute(select(UserRole.role).where(UserRole.user_id == user.id)).scalars().all()
        return user.tenant_id, user.id, set(roles)


@router.post("", response_model=WorkOrderOut)
def create_workorder(payload: WorkOrderCreate, request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)

    require_roles("OWNER", "SUPERVISOR")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        wo = WorkOrder(
            tenant_id=tenant_id,
            site_id=UUID(payload.site_id),
            assigned_tech_user_id=UUID(payload.assigned_tech_user_id),
            scheduled_at=payload.scheduled_at,
            status="SCHEDULED",
        )
        db.add(wo)
        db.flush()
        return WorkOrderOut(
            id=str(wo.id),
            site_id=str(wo.site_id),
            assigned_tech_user_id=str(wo.assigned_tech_user_id),
            scheduled_at=wo.scheduled_at,
            status=wo.status,
        )


@router.get("", response_model=list[WorkOrderOut])
def list_workorders(request: Request, assigned_to: str | None = None):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        stmt = select(WorkOrder)
        if assigned_to == "me":
            require_roles("TECH")
            stmt = stmt.where(WorkOrder.assigned_tech_user_id == user_id)

        rows = db.execute(stmt.order_by(WorkOrder.created_at.desc())).scalars().all()
        return [
            WorkOrderOut(
                id=str(r.id),
                site_id=str(r.site_id),
                assigned_tech_user_id=str(r.assigned_tech_user_id),
                scheduled_at=r.scheduled_at,
                status=r.status,
                visit_status=r.visit_status,
                summary_notes=r.summary_notes,
            )
            for r in rows
        ]


@router.get("/{workorder_id}", response_model=WorkOrderOut)
def get_workorder(workorder_id: str, request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        wo = db.execute(select(WorkOrder).where(WorkOrder.id == UUID(workorder_id))).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")

        # RLS will already prevent cross-tenant access
        return WorkOrderOut(
            id=str(wo.id),
            site_id=str(wo.site_id),
            assigned_tech_user_id=str(wo.assigned_tech_user_id),
            scheduled_at=wo.scheduled_at,
            status=wo.status,
            visit_status=wo.visit_status,
            summary_notes=wo.summary_notes,
        )


@router.post("/{workorder_id}/submit")
def submit_workorder(workorder_id: str, payload: WorkOrderSubmit, request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)

    require_roles("TECH")

    now_iso = datetime.now(timezone.utc).isoformat()

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        wo = db.execute(select(WorkOrder).where(WorkOrder.id == UUID(workorder_id))).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")

        if UUID(str(wo.assigned_tech_user_id)) != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this workorder")

        if wo.status == "SUBMITTED":
            return {"status": "SUBMITTED", "message": "WorkOrder already submitted"}

        if wo.status not in {"SCHEDULED", "IN_PROGRESS"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"WorkOrder cannot be submitted from status {wo.status}",
            )

        wo.status = "SUBMITTED"
        wo.visit_status = payload.visit_status
        wo.summary_notes = payload.summary_notes

        # Idempotent replace of submission data for this workorder.
        db.execute(delete(ChecklistResponse).where(ChecklistResponse.workorder_id == wo.id))
        db.execute(delete(NetMeterReading).where(NetMeterReading.workorder_id == wo.id))
        db.execute(delete(InverterReading).where(InverterReading.workorder_id == wo.id))
        db.execute(delete(Media).where(Media.workorder_id == wo.id))
        db.execute(
            delete(Signature).where(Signature.workorder_id == wo.id, Signature.signer_role == "TECH")
        )

        db.add(ChecklistResponse(
            tenant_id=tenant_id,
            workorder_id=wo.id,
            template_version=1,
            answers_json=payload.checklist_answers,
        ))

        db.add(NetMeterReading(
            tenant_id=tenant_id,
            workorder_id=wo.id,
            net_kwh=payload.net_meter.net_kwh,
            imp_kwh=payload.net_meter.imp_kwh,
            exp_kwh=payload.net_meter.exp_kwh,
        ))

        for r in payload.inverter_readings:
            db.add(InverterReading(
                tenant_id=tenant_id,
                workorder_id=wo.id,
                inverter_id=UUID(r.inverter_id),
                power_kw=r.power_kw,
                day_kwh=r.day_kwh,
                total_kwh=r.total_kwh,
            ))

        for m in payload.media:
            db.add(Media(
                tenant_id=tenant_id,
                workorder_id=wo.id,
                item_key=m.item_key,
                gcs_object_path=m.object_path,
                content_type=m.content_type,
                size_bytes=m.size_bytes,
            ))

        db.add(Signature(
            tenant_id=tenant_id,
            workorder_id=wo.id,
            signer_role="TECH",
            signer_name=payload.tech_signature.signer_name,
            signer_phone=payload.tech_signature.signer_phone,
            signature_gcs_object_path=payload.tech_signature.signature_object_path,
            signed_at=now_iso,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        ))

        return {"status": "SUBMITTED", "message": "WorkOrder submitted successfully"}


@router.patch("/{workorder_id}/status", response_model=WorkOrderOut)
def update_workorder_status(workorder_id: str, payload: WorkOrderStatusUpdate, request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        wo = db.execute(select(WorkOrder).where(WorkOrder.id == UUID(workorder_id))).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")

        target = payload.status
        require_roles("OWNER", "SUPERVISOR", "TECH")

        if target == "IN_PROGRESS":
            if "TECH" in roles and UUID(str(wo.assigned_tech_user_id)) != user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this workorder")
        elif target == "CLOSED":
            require_roles("OWNER", "SUPERVISOR")

        if not _can_transition(wo.status, target):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition {wo.status} -> {target}",
            )

        wo.status = target
        return WorkOrderOut(
            id=str(wo.id),
            site_id=str(wo.site_id),
            assigned_tech_user_id=str(wo.assigned_tech_user_id),
            scheduled_at=wo.scheduled_at,
            status=wo.status,
            visit_status=wo.visit_status,
            summary_notes=wo.summary_notes,
        )
