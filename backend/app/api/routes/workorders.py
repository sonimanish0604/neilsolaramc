from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.security import verify_firebase_jwt
from app.core.tenancy import ctx_roles, ctx_tenant_id, ctx_user_id, require_roles
from app.db.models.site import Customer, Site
from app.db.models.tenant import Tenant
from app.db.session import get_admin_db, get_app_db
from app.db.models.user import User, UserRole
from app.db.models.workorder import (
    ApprovalEvent,
    ChecklistResponse,
    InverterReading,
    Media,
    NetMeterReading,
    Report,
    Signature,
    WorkOrder,
)
from app.schemas.workorders import (
    SendApprovalIn,
    SendApprovalOut,
    WorkOrderCreate,
    WorkOrderOut,
    WorkOrderStatusUpdate,
    WorkOrderSubmit,
)
from app.services.approval_tokens import compute_expiry_iso, generate_approval_token
from app.services.notification_events import publish_notification_event
from app.services.report_generator import ReportRenderContext, generate_report_pdf

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


def _approval_base_url(request: Request | None = None) -> str:
    configured = (settings.approval_base_url or "").strip().rstrip("/")
    # Local/dev simulation should generate directly usable links out of the box.
    if request and settings.app_env.lower() in {"local", "dev", "test"}:
        if not configured or configured == "https://app.neilsolar.com/approve":
            return f"{str(request.base_url).rstrip('/')}/approve"
    if configured:
        return configured
    if request:
        return f"{str(request.base_url).rstrip('/')}/approve"
    return "https://app.neilsolar.com/approve"


def _approval_link(token: str, request: Request | None = None) -> str:
    return f"{_approval_base_url(request).rstrip('/')}/{token}"


def _approval_report_link(token: str, request: Request | None = None) -> str:
    return f"{_approval_base_url(request).rstrip('/')}/{token}/report"


def _approval_message(site_name: str, approval_url: str, report_url: str, expires_at: str) -> str:
    return (
        f"{settings.pdf_brand_label}: Your service report for {site_name} is ready. "
        f"Report PDF: {report_url} "
        f"Please review and sign here: {approval_url} "
        f"(link expires at {expires_at})."
    )


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

        site = db.execute(select(Site).where(Site.id == wo.site_id)).scalar_one_or_none()
        publish_notification_event(
            db=db,
            tenant_id=tenant_id,
            event_type="work_order.completed",
            entity_type="work_order",
            entity_id=str(wo.id),
            payload={
                "workorder_id": str(wo.id),
                "site_name": site.site_name if site else None,
                "site_supervisor_email": site.site_supervisor_email if site else None,
                "site_supervisor_phone": site.site_supervisor_phone if site else None,
                "visit_status": wo.visit_status,
                "summary_notes": wo.summary_notes,
                "technician_name": payload.tech_signature.signer_name,
            },
        )

        return {"status": "SUBMITTED", "message": "WorkOrder submitted successfully"}


@router.post("/{workorder_id}/send-approval", response_model=SendApprovalOut)
def send_approval(workorder_id: str, payload: SendApprovalIn, request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)

    require_roles("OWNER", "SUPERVISOR")

    with get_admin_db() as adb:
        tenant = adb.execute(select(Tenant).where(Tenant.id == tenant_id)).scalar_one_or_none()
        tenant_logo_path = tenant.logo_object_path if tenant else None

    expires_at = compute_expiry_iso(settings.approval_token_ttl_hours)
    token = generate_approval_token()
    approval_url = _approval_link(token, request)
    report_url = _approval_report_link(token, request)

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        wo = db.execute(select(WorkOrder).where(WorkOrder.id == UUID(workorder_id))).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")
        if wo.status != "SUBMITTED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Approval link can only be sent for SUBMITTED workorders, got {wo.status}",
            )

        site = db.execute(select(Site).where(Site.id == wo.site_id)).scalar_one_or_none()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        if payload.channel == "WHATSAPP" and not site.site_supervisor_phone:
            raise HTTPException(status_code=400, detail="Site supervisor phone is required")
        if payload.channel == "EMAIL" and not site.site_supervisor_email:
            raise HTTPException(status_code=400, detail="Site supervisor email is required")

        customer = db.execute(select(Customer).where(Customer.id == site.customer_id)).scalar_one_or_none()
        customer_logo_path = customer.logo_object_path if customer else None

        latest_report = db.execute(
            select(Report).where(Report.workorder_id == wo.id).order_by(Report.generated_at.desc())
        ).scalar_one_or_none()
        if not latest_report:
            rendered = generate_report_pdf(
                str(wo.id),
                report_version=1,
                context=ReportRenderContext(
                    site_name=site.site_name,
                    visit_status=wo.visit_status,
                    brand_label=settings.pdf_brand_label,
                    logo_object_path=customer_logo_path or tenant_logo_path,
                    summary_notes=wo.summary_notes,
                ),
            )
            latest_report = Report(
                tenant_id=tenant_id,
                workorder_id=wo.id,
                report_version=1,
                pdf_gcs_object_path=rendered.gcs_object_path,
                pdf_sha256=rendered.sha256,
                pass_count=rendered.pass_count,
                fail_count=rendered.fail_count,
                generated_at=rendered.generated_at_iso,
                is_final=False,
            )
            db.add(latest_report)

        existing = db.execute(
            select(ApprovalEvent).where(
                ApprovalEvent.workorder_id == wo.id,
                ApprovalEvent.status.in_(["QUEUED", "SENT", "OPENED"]),
            )
        ).scalars().all()
        for event in existing:
            event.status = "REVOKED"

        event = ApprovalEvent(
            tenant_id=tenant_id,
            workorder_id=wo.id,
            channel=payload.channel,
            token=token,
            expires_at=expires_at,
            status="QUEUED",
        )
        db.add(event)
        db.flush()

        notification_event = publish_notification_event(
            db=db,
            tenant_id=tenant_id,
            event_type="work_order.submitted_for_approval",
            entity_type="work_order",
            entity_id=str(wo.id),
            payload={
                "approval_token": token,
                "approval_url": approval_url,
                "report_url": report_url,
                "expires_at": expires_at,
                "channels": [payload.channel],
                "site_name": site.site_name,
                "site_supervisor_phone": site.site_supervisor_phone,
                "site_supervisor_email": site.site_supervisor_email,
                "message": _approval_message(site.site_name, approval_url, report_url, expires_at),
                "workorder_id": str(wo.id),
                "tenant_id": str(tenant_id),
            },
        )

        return SendApprovalOut(
            status=event.status,
            channel=event.channel,
            expires_at=event.expires_at,
            approval_token=event.token,
            approval_url=approval_url,
            report_url=report_url,
            delivery_status="QUEUED",
            provider_message_id=None,
            detail=f"Notification event queued: {notification_event.id}",
        )


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
