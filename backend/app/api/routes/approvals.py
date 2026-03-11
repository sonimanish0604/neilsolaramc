from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import select

from app.core.config import settings
from app.core.correlation import get_request_correlation_id
from app.core.tenancy import ctx_roles, ctx_tenant_id, ctx_user_id
from app.db.models.site import Site
from app.db.models.workorder import ApprovalEvent, Report, Signature, WorkOrder
from app.db.session import get_admin_db, get_app_db
from app.schemas.approvals import ApprovalViewOut, CustomerSignIn, CustomerSignOut
from app.services.approval_tokens import is_expired_iso
from app.services.report_jobs import enqueue_report_job, run_report_job
from app.services.report_storage import load_report_pdf

router = APIRouter(prefix="/approve", tags=["approvals"])


@dataclass(frozen=True)
class ResolvedApprovalToken:
    approval_event_id: UUID
    tenant_id: UUID
    workorder_id: UUID
    token: str
    status: str
    correlation_id: str | None


def _approval_base_url(request: Request | None = None) -> str:
    configured = (settings.approval_base_url or "").strip().rstrip("/")
    if request and settings.app_env.lower() in {"local", "dev", "test"}:
        if not configured or configured == "https://app.neilsolar.com/approve":
            return f"{str(request.base_url).rstrip('/')}/approve"
    if configured:
        return configured
    if request:
        return f"{str(request.base_url).rstrip('/')}/approve"
    return "https://app.neilsolar.com/approve"


def _approval_report_link(token: str, request: Request | None = None) -> str:
    return f"{_approval_base_url(request).rstrip('/')}/{token}/report"


def _resolve_token_event(
    token: str,
    *,
    mark_opened: bool = False,
    allow_used: bool = False,
) -> ResolvedApprovalToken:
    with get_admin_db() as adb:
        ae = adb.execute(select(ApprovalEvent).where(ApprovalEvent.token == token)).scalar_one_or_none()
        if not ae:
            raise HTTPException(status_code=404, detail="Invalid token")

        if is_expired_iso(ae.expires_at):
            ae.status = "EXPIRED"
            adb.commit()
            raise HTTPException(status_code=410, detail="Token expired")

        if ae.status in {"SUPERSEDED", "REVOKED"}:
            raise HTTPException(status_code=410, detail="Token no longer valid")
        if ae.status in {"SEND_FAILED", "DELIVERY_PERMANENT_FAILED"}:
            raise HTTPException(status_code=409, detail=f"Token unavailable ({ae.status})")
        if not allow_used and ae.status in {"SIGNED", "CONSUMED"}:
            raise HTTPException(status_code=409, detail="Token already used")

        if mark_opened and ae.status in {"QUEUED", "SENT", "DELIVERY_FAILED"}:
            ae.status = "OPENED"
            ae.opened_at = datetime.now(timezone.utc).isoformat()
            adb.commit()

        return ResolvedApprovalToken(
            approval_event_id=ae.id,
            tenant_id=ae.tenant_id,
            workorder_id=ae.workorder_id,
            token=ae.token,
            status=ae.status,
            correlation_id=ae.correlation_id,
        )


@router.get("/{token}", response_model=ApprovalViewOut)
def view_approval(token: str, request: Request):
    event = _resolve_token_event(token, mark_opened=True)
    ctx_tenant_id.set(event.tenant_id)
    ctx_user_id.set(None)
    ctx_roles.set(set())

    with get_app_db(tenant_id=event.tenant_id, user_id=None) as db:
        wo = db.execute(select(WorkOrder).where(WorkOrder.id == event.workorder_id)).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")

        site = db.execute(select(Site).where(Site.id == wo.site_id)).scalar_one_or_none()
        rpt = db.execute(
            select(Report).where(Report.workorder_id == wo.id).order_by(Report.generated_at.desc())
        ).scalar_one_or_none()

        return ApprovalViewOut(
            workorder_id=str(wo.id),
            site_name=site.site_name if site else "Unknown site",
            scheduled_at=wo.scheduled_at,
            visit_status=wo.visit_status,
            summary={"pass_count": rpt.pass_count if rpt else 0, "fail_count": rpt.fail_count if rpt else 0},
            report_pdf_url=_approval_report_link(token, request) if rpt else None,
            sign_required=True,
        )


@router.get("/{token}/report")
def view_approval_report(token: str):
    event = _resolve_token_event(token, allow_used=True)
    ctx_tenant_id.set(event.tenant_id)
    ctx_user_id.set(None)
    ctx_roles.set(set())

    with get_app_db(tenant_id=event.tenant_id, user_id=None) as db:
        rpt = db.execute(
            select(Report).where(Report.workorder_id == event.workorder_id).order_by(Report.generated_at.desc())
        ).scalar_one_or_none()
        if not rpt:
            raise HTTPException(status_code=404, detail="Report not found")
        pdf_bytes = load_report_pdf(rpt.pdf_gcs_object_path)

    filename = f"workorder-{event.workorder_id}-report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/{token}/sign", response_model=CustomerSignOut)
def customer_sign(token: str, payload: CustomerSignIn, request: Request):
    correlation_id = get_request_correlation_id(request)
    event = _resolve_token_event(token)
    ctx_tenant_id.set(event.tenant_id)
    ctx_user_id.set(None)
    ctx_roles.set(set())

    now_iso = datetime.now(timezone.utc).isoformat()

    with get_app_db(tenant_id=event.tenant_id, user_id=None) as db:
        wo = db.execute(select(WorkOrder).where(WorkOrder.id == event.workorder_id)).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")
        if wo.status in {"CUSTOMER_SIGNED", "CLOSED"}:
            raise HTTPException(status_code=409, detail=f"WorkOrder is in {wo.status}, cannot sign")

        existing_customer_signature = db.execute(
            select(Signature).where(
                Signature.workorder_id == wo.id,
                Signature.signer_role == "CUSTOMER_SUPERVISOR",
            )
        ).scalar_one_or_none()
        if existing_customer_signature:
            raise HTTPException(status_code=409, detail="Customer signature already exists for this workorder")

        db.add(
            Signature(
                tenant_id=event.tenant_id,
                workorder_id=wo.id,
                signer_role="CUSTOMER_SUPERVISOR",
                signer_name=payload.signer_name,
                signer_phone=payload.signer_phone,
                signature_gcs_object_path=payload.signature_object_path,
                signed_at=now_iso,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            )
        )

        wo.status = "CUSTOMER_SIGNED"

        final_job = enqueue_report_job(
            db,
            tenant_id=event.tenant_id,
            workorder_id=wo.id,
            is_final=True,
            idempotency_key=f"approval-final:{event.approval_event_id}",
            correlation_id=event.correlation_id or correlation_id,
        )
        final_job_result = run_report_job(db, job=final_job, force=True)

    with get_admin_db() as adb:
        ae = adb.execute(select(ApprovalEvent).where(ApprovalEvent.id == event.approval_event_id)).scalar_one_or_none()
        if ae:
            ae.status = "SIGNED"
            ae.signed_at = now_iso
            ae.next_retry_at = None
            adb.commit()

    if final_job_result.report:
        return CustomerSignOut(
            status="SIGNED",
            final_report_pdf_url=_approval_report_link(token, request),
        )
    return CustomerSignOut(status="SIGNED_REPORT_PENDING", final_report_pdf_url=None)
