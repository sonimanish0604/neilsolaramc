from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import select

from app.core.config import settings
from app.core.tenancy import ctx_roles, ctx_tenant_id, ctx_user_id
from app.db.session import get_admin_db, get_app_db
from app.db.models.site import Customer, Site
from app.db.models.tenant import Tenant
from app.db.models.workorder import WorkOrder, ApprovalEvent, Signature, Report
from app.schemas.approvals import ApprovalViewOut, CustomerSignIn, CustomerSignOut
from app.services.approval_tokens import is_expired_iso
from app.services.report_generator import ReportRenderContext, generate_report_pdf
from app.services.report_storage import load_report_pdf

router = APIRouter(prefix="/approve", tags=["approvals"])


@dataclass(frozen=True)
class ResolvedApprovalToken:
    tenant_id: UUID
    workorder_id: UUID
    token: str
    status: str


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
    mark_opened: bool = False,
    allow_used: bool = False,
) -> ResolvedApprovalToken:
    """
    Uses ADMIN DB (BYPASSRLS) to resolve and validate approval token lifecycle.
    """
    with get_admin_db() as adb:
        ae = adb.execute(select(ApprovalEvent).where(ApprovalEvent.token == token)).scalar_one_or_none()
        if not ae:
            raise HTTPException(status_code=404, detail="Invalid token")

        if is_expired_iso(ae.expires_at):
            ae.status = "EXPIRED"
            adb.commit()
            raise HTTPException(status_code=410, detail="Token expired")

        if not allow_used and ae.status in {"SIGNED", "CONSUMED"}:
            raise HTTPException(status_code=409, detail="Token already used")
        if ae.status in {"REVOKED", "SEND_FAILED"}:
            raise HTTPException(status_code=409, detail=f"Token unavailable ({ae.status})")

        if mark_opened and ae.status in {"QUEUED", "SENT"}:
            ae.status = "OPENED"
            adb.commit()

        return ResolvedApprovalToken(
            tenant_id=ae.tenant_id,
            workorder_id=ae.workorder_id,
            token=ae.token,
            status=ae.status,
        )


@router.get("/{token}", response_model=ApprovalViewOut)
def view_approval(token: str, request: Request):
    event = _resolve_token_event(token, mark_opened=True)
    tenant_id, workorder_id = event.tenant_id, event.workorder_id

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(None)
    ctx_roles.set(set())

    with get_app_db(tenant_id=tenant_id, user_id=None) as db:
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
            report_pdf_url=_approval_report_link(token, request) if rpt else None,
            sign_required=True,
        )


@router.get("/{token}/report")
def view_approval_report(token: str):
    event = _resolve_token_event(token, allow_used=True)
    tenant_id, workorder_id = event.tenant_id, event.workorder_id

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(None)
    ctx_roles.set(set())

    with get_app_db(tenant_id=tenant_id, user_id=None) as db:
        rpt = db.execute(
            select(Report).where(Report.workorder_id == workorder_id).order_by(Report.generated_at.desc())
        ).scalar_one_or_none()
        if not rpt:
            raise HTTPException(status_code=404, detail="Report not found")
        pdf_bytes = load_report_pdf(rpt.pdf_gcs_object_path)

    filename = f"workorder-{workorder_id}-report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/{token}/sign", response_model=CustomerSignOut)
def customer_sign(token: str, payload: CustomerSignIn, request: Request):
    event = _resolve_token_event(token)
    tenant_id, workorder_id = event.tenant_id, event.workorder_id

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(None)
    ctx_roles.set(set())

    now_iso = datetime.now(timezone.utc).isoformat()

    with get_admin_db() as adb:
        tenant = adb.execute(select(Tenant).where(Tenant.id == tenant_id)).scalar_one_or_none()
        tenant_logo_path = tenant.logo_object_path if tenant else None

    with get_app_db(tenant_id=tenant_id, user_id=None) as db:
        wo = db.execute(select(WorkOrder).where(WorkOrder.id == workorder_id)).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")
        if wo.status != "SUBMITTED":
            raise HTTPException(status_code=409, detail=f"WorkOrder is in {wo.status}, cannot sign")

        existing_customer_signature = db.execute(
            select(Signature).where(
                Signature.workorder_id == wo.id,
                Signature.signer_role == "CUSTOMER_SUPERVISOR",
            )
        ).scalar_one_or_none()
        if existing_customer_signature:
            raise HTTPException(status_code=409, detail="Customer signature already exists for this workorder")

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

        site = db.execute(select(Site).where(Site.id == wo.site_id)).scalar_one_or_none()
        customer_logo_path = None
        if site:
            customer = db.execute(select(Customer).where(Customer.id == site.customer_id)).scalar_one_or_none()
            customer_logo_path = customer.logo_object_path if customer else None

        # mark status then generate branded final report
        wo.status = "CUSTOMER_SIGNED"

        previous_report = db.execute(
            select(Report).where(Report.workorder_id == wo.id).order_by(Report.generated_at.desc())
        ).scalar_one_or_none()
        next_version = (previous_report.report_version + 1) if previous_report else 2

        gen = generate_report_pdf(
            str(wo.id),
            report_version=next_version,
            context=ReportRenderContext(
                site_name=site.site_name if site else None,
                visit_status=wo.visit_status,
                brand_label=settings.pdf_brand_label,
                logo_object_path=customer_logo_path or tenant_logo_path,
                include_customer_signature=True,
                summary_notes=wo.summary_notes,
            ),
        )
        final_report = Report(
            tenant_id=tenant_id,
            workorder_id=wo.id,
            report_version=next_version,
            pdf_gcs_object_path=gen.gcs_object_path,
            pdf_sha256=gen.sha256,
            pass_count=gen.pass_count,
            fail_count=gen.fail_count,
            generated_at=gen.generated_at_iso,
            is_final=True,
        )
        db.add(final_report)

    with get_admin_db() as adb:
        ae = adb.execute(select(ApprovalEvent).where(ApprovalEvent.token == token)).scalar_one_or_none()
        if ae:
            ae.status = "SIGNED"
            adb.commit()

    return CustomerSignOut(
        status="SIGNED",
        final_report_pdf_url=_approval_report_link(token, request),
    )
