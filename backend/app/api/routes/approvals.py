from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.core.tenancy import ctx_roles, ctx_tenant_id, ctx_user_id
from app.core.correlation import get_request_correlation_id
from app.db.session import get_admin_db, get_app_db
from app.db.models.site import Site
from app.db.models.workorder import WorkOrder, ApprovalEvent, Report, Signature
from app.schemas.approvals import ApprovalViewOut, CustomerSignIn, CustomerSignOut
from app.services.approval_tokens import now_utc, parse_iso
from app.services.report_jobs import enqueue_report_job, run_report_job

router = APIRouter(prefix="/approve", tags=["approvals"])


def _resolve_token_to_context(token: str):
    """
    Uses ADMIN DB (BYPASSRLS) to resolve token -> (tenant_id, workorder_id).
    """
    with get_admin_db() as adb:
        ae = adb.execute(select(ApprovalEvent).where(ApprovalEvent.token == token)).scalar_one_or_none()
        if not ae:
            raise HTTPException(status_code=404, detail="Invalid token")

        if ae.status in {"SUPERSEDED", "REVOKED"}:
            raise HTTPException(status_code=410, detail="Token no longer valid")
        if ae.status == "SIGNED":
            raise HTTPException(status_code=409, detail="Token already used")

        # expiry check
        exp = parse_iso(ae.expires_at)
        if exp < now_utc():
            ae.status = "EXPIRED"
            adb.commit()
            raise HTTPException(status_code=410, detail="Token expired")

        return ae.tenant_id, ae.workorder_id, ae.id


@router.get("/{token}", response_model=ApprovalViewOut)
def view_approval(token: str):
    tenant_id, workorder_id, approval_event_id = _resolve_token_to_context(token)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(None)
    ctx_roles.set(set())

    with get_app_db(tenant_id=tenant_id, user_id=None) as db:
        approval_event = db.execute(select(ApprovalEvent).where(ApprovalEvent.id == approval_event_id)).scalar_one()
        if approval_event.status in {"SENT", "DELIVERY_FAILED", "QUEUED"}:
            approval_event.status = "OPENED"
            approval_event.opened_at = datetime.now(timezone.utc).isoformat()

        wo = db.execute(select(WorkOrder).where(WorkOrder.id == workorder_id)).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")

        site = db.execute(select(Site).where(Site.id == wo.site_id)).scalar_one_or_none()
        site_name = site.site_name if site else "Unknown site"

        # latest report if exists
        rpt = db.execute(
            select(Report).where(Report.workorder_id == wo.id).order_by(Report.generated_at.desc())
        ).scalar_one_or_none()

        return ApprovalViewOut(
            workorder_id=str(wo.id),
            site_name=site_name,
            scheduled_at=wo.scheduled_at,
            visit_status=wo.visit_status,
            summary={"pass_count": rpt.pass_count if rpt else 0, "fail_count": rpt.fail_count if rpt else 0},
            report_pdf_url=rpt.pdf_gcs_object_path if rpt else None,
            sign_required=True,
        )


@router.post("/{token}/sign", response_model=CustomerSignOut)
def customer_sign(token: str, payload: CustomerSignIn, request: Request):
    correlation_id = get_request_correlation_id(request)
    tenant_id, workorder_id, approval_event_id = _resolve_token_to_context(token)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(None)
    ctx_roles.set(set())

    now_iso = datetime.now(timezone.utc).isoformat()

    with get_app_db(tenant_id=tenant_id, user_id=None) as db:
        approval_event = db.execute(select(ApprovalEvent).where(ApprovalEvent.id == approval_event_id)).scalar_one()
        if approval_event.status == "SIGNED":
            raise HTTPException(status_code=409, detail="Token already used")

        wo = db.execute(select(WorkOrder).where(WorkOrder.id == workorder_id)).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")

        # store customer signature
        db.add(Signature(
            tenant_id=tenant_id,
            workorder_id=wo.id,
            signer_role="CUSTOMER_SUPERVISOR",
            signer_name=payload.signer_name,
            signer_phone=payload.signer_phone,
            signature_gcs_object_path=payload.signature_object_path,
            signed_at=now_iso,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        ))

        # mark status
        wo.status = "CUSTOMER_SIGNED"

        final_job = enqueue_report_job(
            db,
            tenant_id=tenant_id,
            workorder_id=wo.id,
            is_final=True,
            idempotency_key=f"approval-final:{approval_event.id}",
            correlation_id=approval_event.correlation_id or correlation_id,
        )
        final_job_result = run_report_job(db, job=final_job, force=True)
        approval_event.status = "SIGNED"
        approval_event.signed_at = now_iso
        approval_event.next_retry_at = None

        if final_job_result.report:
            return CustomerSignOut(status="SIGNED", final_report_pdf_url=final_job_result.report.pdf_gcs_object_path)
        return CustomerSignOut(status="SIGNED_REPORT_PENDING", final_report_pdf_url=None)
