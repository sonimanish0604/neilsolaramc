from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import delete, select

from app.core.correlation import get_request_correlation_id
from app.core.security import verify_firebase_jwt
from app.core.tenancy import ctx_roles, ctx_tenant_id, ctx_user_id, require_roles
from app.db.models.site import Site
from app.db.models.user import User, UserRole
from app.db.models.workorder import (
    ApprovalEvent,
    ChecklistResponse,
    InverterReading,
    Media,
    NetMeterReading,
    Report,
    ReportJob,
    Signature,
    WorkOrder,
)
from app.db.session import get_admin_db, get_app_db
from app.schemas.workorders import (
    ApprovalReminderRunOut,
    ApprovalResendIn,
    ApprovalSendOut,
    GenerateReportSyncOut,
    InverterReadingCaptureIn,
    InverterReadingCaptureOut,
    ReportJobCreateIn,
    ReportJobOut,
    SendApprovalIn,
    WorkOrderConfiguredInverterOut,
    WorkOrderInverterListOut,
    WorkOrderCreate,
    WorkOrderOut,
    WorkOrderReportDataOut,
    WorkOrderStatusUpdate,
    WorkOrderSubmit,
)
from app.services.approval_tokens import (
    build_approval_link,
    create_and_send_approval_event,
    latest_active_event,
    now_utc,
    parse_iso,
    process_due_reminders,
    resend_approval_link,
)
from app.services.inverter_readings import (
    CaptureReadingInput,
    ensure_site_inverter_capture_complete,
    get_site_inverter,
    latest_accepted_reading,
    list_site_inverters,
    to_float,
    upsert_workorder_inverter_reading,
)
from app.services.notification_events import publish_notification_event
from app.services.report_jobs import enqueue_report_job, retry_report_job, run_report_job
from app.services.report_summary import build_workorder_generation_summary, report_generation_summary

router = APIRouter(prefix="/workorders", tags=["workorders"])


def _can_transition(current_status: str, next_status: str) -> bool:
    allowed = {
        "SCHEDULED": {"IN_PROGRESS"},
        "CUSTOMER_SIGNED": {"CLOSED"},
    }
    return next_status in allowed.get(current_status, set())


def _approval_event_out(event: ApprovalEvent) -> ApprovalSendOut:
    approval_link = build_approval_link(event.token)
    report_link = f"{approval_link}/report"
    delivery_status = "SENT" if event.status in {"SENT", "OPENED"} else event.status
    return ApprovalSendOut(
        event_id=str(event.id),
        correlation_id=event.correlation_id,
        workorder_id=str(event.workorder_id),
        channel=event.channel,
        recipient=event.recipient,
        status=event.status,
        token_expires_at=event.expires_at,
        approval_link=approval_link,
        attempt_count=event.attempt_count,
        next_retry_at=event.next_retry_at,
        approval_token=event.token,
        approval_url=approval_link,
        report_url=report_link,
        delivery_status=delivery_status,
        provider_message_id=None,
        detail=None,
    )


def _report_job_out(job: ReportJob, report: Report | None = None) -> ReportJobOut:
    resolved_report = report
    if not resolved_report and job.generated_report_id:
        resolved_report_id = str(job.generated_report_id)
    else:
        resolved_report_id = str(resolved_report.id) if resolved_report else None

    return ReportJobOut(
        job_id=str(job.id),
        correlation_id=job.correlation_id,
        workorder_id=str(job.workorder_id),
        job_type=job.job_type,
        status=job.status,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        next_retry_at=job.next_retry_at,
        last_error=job.last_error,
        generated_report_id=resolved_report_id,
        report_pdf_url=resolved_report.pdf_gcs_object_path if resolved_report else None,
    )


def _configured_inverter_out(db, workorder: WorkOrder, inverter) -> WorkOrderConfiguredInverterOut:
    previous = latest_accepted_reading(db, inverter_id=inverter.id, current_workorder_id=workorder.id)
    previous_value = None
    if previous:
        previous_value = to_float(previous.current_reading_kwh or previous.total_kwh)
    return WorkOrderConfiguredInverterOut(
        inverter_id=str(inverter.id),
        inverter_code=inverter.inverter_code,
        display_name=inverter.display_name,
        capacity_kw=to_float(inverter.capacity_kw),
        latest_accepted_reading_kwh=previous_value,
    )


def _capture_out(db, inverter, reading: InverterReading) -> InverterReadingCaptureOut:
    media = db.execute(select(Media).where(Media.inverter_reading_id == reading.id)).scalar_one_or_none()
    return InverterReadingCaptureOut(
        reading_id=str(reading.id),
        inverter_id=str(inverter.id),
        inverter_code=inverter.inverter_code,
        display_name=inverter.display_name,
        previous_reading_kwh=to_float(reading.previous_reading_kwh),
        current_reading_kwh=to_float(reading.current_reading_kwh),
        generation_delta_kwh=to_float(reading.generation_delta_kwh),
        is_baseline=reading.is_baseline,
        is_anomaly=reading.is_anomaly,
        anomaly_reason=reading.anomaly_reason,
        device_latitude=to_float(reading.device_latitude),
        device_longitude=to_float(reading.device_longitude),
        device_accuracy_meters=to_float(reading.device_accuracy_meters),
        distance_to_site_meters=to_float(reading.distance_to_site_meters),
        geo_validation_status=reading.geo_validation_status,
        geo_validation_reason=reading.geo_validation_reason,
        operational_status=reading.operational_status,
        remarks=reading.remarks,
        photo_object_path=media.gcs_object_path if media else "",
    )


def _report_data_out(summary) -> WorkOrderReportDataOut:
    return WorkOrderReportDataOut(
        workorder_id=str(summary.workorder_id),
        site_id=str(summary.site_id),
        generation_total_kwh=summary.generation_total_kwh,
        baseline_inverter_count=summary.baseline_inverter_count,
        anomaly_count=summary.anomaly_count,
        inverters=[
            {
                "inverter_id": str(row.inverter_id),
                "inverter_code": row.inverter_code,
                "display_name": row.display_name,
                "previous_reading_kwh": row.previous_reading_kwh,
                "current_reading_kwh": row.current_reading_kwh,
                "generation_delta_kwh": row.generation_delta_kwh,
                "is_baseline": row.is_baseline,
                "is_anomaly": row.is_anomaly,
                "anomaly_reason": row.anomaly_reason,
                "operational_status": row.operational_status,
                "remarks": row.remarks,
                "photo_object_path": row.photo_object_path,
            }
            for row in summary.inverters
        ],
    )


def _load_user_and_tenant(firebase_uid: str):
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

        return WorkOrderOut(
            id=str(wo.id),
            site_id=str(wo.site_id),
            assigned_tech_user_id=str(wo.assigned_tech_user_id),
            scheduled_at=wo.scheduled_at,
            status=wo.status,
            visit_status=wo.visit_status,
            summary_notes=wo.summary_notes,
        )


@router.get("/{workorder_id}/inverters", response_model=WorkOrderInverterListOut)
def list_workorder_inverters(workorder_id: str, request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)
    require_roles("OWNER", "SUPERVISOR", "TECH")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        wo = db.execute(select(WorkOrder).where(WorkOrder.id == UUID(workorder_id))).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")

        inverters = list_site_inverters(db, site_id=wo.site_id, active_only=True)
        return WorkOrderInverterListOut(
            workorder_id=str(wo.id),
            site_id=str(wo.site_id),
            inverters=[_configured_inverter_out(db, wo, inverter) for inverter in inverters],
        )


@router.post("/{workorder_id}/inverter-readings", response_model=InverterReadingCaptureOut)
def capture_inverter_reading(workorder_id: str, payload: InverterReadingCaptureIn, request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)
    require_roles("TECH")

    captured_at_iso = datetime.now(timezone.utc).isoformat()

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        wo = db.execute(select(WorkOrder).where(WorkOrder.id == UUID(workorder_id))).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")
        if UUID(str(wo.assigned_tech_user_id)) != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this workorder")
        if wo.status in {"CUSTOMER_SIGNED", "CLOSED"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="WorkOrder is locked for reading updates")

        inverter = get_site_inverter(db, site_id=wo.site_id, inverter_id=UUID(payload.inverter_id))
        if not inverter:
            raise HTTPException(status_code=404, detail="Configured site inverter not found")
        if not inverter.is_active:
            raise HTTPException(status_code=409, detail="Inactive site inverter cannot be captured")
        site = db.execute(select(Site).where(Site.id == wo.site_id)).scalar_one_or_none()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")

        reading = upsert_workorder_inverter_reading(
            db,
            tenant_id=tenant_id,
            workorder=wo,
            inverter=inverter,
            capture=CaptureReadingInput(
                current_reading_kwh=payload.current_reading_kwh,
                operational_status=payload.operational_status,
                remarks=payload.remarks,
                photo_object_path=payload.photo_object_path,
                photo_content_type=payload.photo_content_type,
                photo_size_bytes=payload.photo_size_bytes,
                site_latitude=to_float(site.site_latitude),
                site_longitude=to_float(site.site_longitude),
                device_latitude=payload.device_latitude,
                device_longitude=payload.device_longitude,
                device_accuracy_meters=payload.device_accuracy_meters,
            ),
            captured_at_iso=captured_at_iso,
        )
        return _capture_out(db, inverter, reading)


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
        configured_inverters = list_site_inverters(db, site_id=wo.site_id, active_only=True)

        db.execute(delete(ChecklistResponse).where(ChecklistResponse.workorder_id == wo.id))
        db.execute(delete(NetMeterReading).where(NetMeterReading.workorder_id == wo.id))
        db.execute(delete(Media).where(Media.workorder_id == wo.id, Media.inverter_reading_id.is_(None)))
        db.execute(delete(Signature).where(Signature.workorder_id == wo.id, Signature.signer_role == "TECH"))

        db.add(
            ChecklistResponse(
                tenant_id=tenant_id,
                workorder_id=wo.id,
                template_version=1,
                answers_json=payload.checklist_answers,
            )
        )
        db.add(
            NetMeterReading(
                tenant_id=tenant_id,
                workorder_id=wo.id,
                net_kwh=payload.net_meter.net_kwh,
                imp_kwh=payload.net_meter.imp_kwh,
                exp_kwh=payload.net_meter.exp_kwh,
            )
        )

        if configured_inverters:
            capture_errors = ensure_site_inverter_capture_complete(db, workorder=wo)
            if capture_errors:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(capture_errors))
        else:
            db.execute(delete(InverterReading).where(InverterReading.workorder_id == wo.id))
            for reading in payload.inverter_readings:
                current_reading_kwh = reading.total_kwh
                previous = latest_accepted_reading(
                    db,
                    inverter_id=UUID(reading.inverter_id),
                    current_workorder_id=wo.id,
                )
                previous_reading_kwh = to_float(previous.current_reading_kwh or previous.total_kwh) if previous else None
                is_baseline = current_reading_kwh is not None and previous_reading_kwh is None
                is_anomaly = (
                    current_reading_kwh is not None
                    and previous_reading_kwh is not None
                    and current_reading_kwh < previous_reading_kwh
                )
                generation_delta_kwh = None
                if (
                    current_reading_kwh is not None
                    and previous_reading_kwh is not None
                    and not is_anomaly
                ):
                    generation_delta_kwh = current_reading_kwh - previous_reading_kwh
                db.add(
                    InverterReading(
                        tenant_id=tenant_id,
                        workorder_id=wo.id,
                        inverter_id=UUID(reading.inverter_id),
                        power_kw=reading.power_kw,
                        day_kwh=reading.day_kwh,
                        total_kwh=reading.total_kwh,
                        current_reading_kwh=current_reading_kwh,
                        previous_reading_kwh=previous_reading_kwh,
                        generation_delta_kwh=generation_delta_kwh,
                        is_baseline=is_baseline,
                        is_anomaly=is_anomaly,
                        anomaly_reason=(
                            "Current reading is lower than the latest accepted reading" if is_anomaly else None
                        ),
                        operational_status=reading.operational_status or "OPERATIONAL",
                        remarks=reading.remarks,
                        captured_at=now_iso,
                    )
                )

        for media_item in payload.media:
            db.add(
                Media(
                    tenant_id=tenant_id,
                    workorder_id=wo.id,
                    item_key=media_item.item_key,
                    gcs_object_path=media_item.object_path,
                    content_type=media_item.content_type,
                    size_bytes=media_item.size_bytes,
                )
            )

        db.add(
            Signature(
                tenant_id=tenant_id,
                workorder_id=wo.id,
                signer_role="TECH",
                signer_name=payload.tech_signature.signer_name,
                signer_phone=payload.tech_signature.signer_phone,
                signature_gcs_object_path=payload.tech_signature.signature_object_path,
                signed_at=now_iso,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            )
        )

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


@router.get("/{workorder_id}/report-data", response_model=WorkOrderReportDataOut)
def get_workorder_report_data(workorder_id: str, request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)
    require_roles("OWNER", "SUPERVISOR", "TECH")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        wo = db.execute(select(WorkOrder).where(WorkOrder.id == UUID(workorder_id))).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")

        latest_report = db.execute(
            select(Report).where(Report.workorder_id == wo.id).order_by(Report.report_version.desc())
        ).scalars().first()
        if latest_report and latest_report.generation_snapshot_json:
            summary = report_generation_summary(latest_report)
            if summary:
                return _report_data_out(summary)

        return _report_data_out(build_workorder_generation_summary(db, workorder=wo))


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


@router.post("/{workorder_id}/send-approval", response_model=ApprovalSendOut)
def send_approval_link(workorder_id: str, request: Request, payload: SendApprovalIn | None = None):
    correlation_id = get_request_correlation_id(request)
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)
    require_roles("OWNER", "SUPERVISOR")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        wo = db.execute(select(WorkOrder).where(WorkOrder.id == UUID(workorder_id))).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")
        if wo.status in {"CUSTOMER_SIGNED", "CLOSED"}:
            raise HTTPException(status_code=409, detail=f"Approval link not allowed for status {wo.status}")

        active_event = latest_active_event(db, wo.id)
        if active_event and parse_iso(active_event.expires_at) > now_utc():
            raise HTTPException(
                status_code=409,
                detail="Active approval token already exists. Use /resend-approval for reminder/refresh.",
            )
        if active_event and parse_iso(active_event.expires_at) <= now_utc():
            active_event.status = "EXPIRED"

        preferred_channel = payload.channel if payload else None
        if preferred_channel:
            site = db.execute(select(Site).where(Site.id == wo.site_id)).scalar_one_or_none()
            if not site:
                raise HTTPException(status_code=404, detail="Site not found")
            if preferred_channel == "EMAIL" and not site.site_supervisor_email:
                raise HTTPException(status_code=400, detail="Site supervisor email is required")
            if preferred_channel == "WHATSAPP" and not site.site_supervisor_phone:
                raise HTTPException(status_code=400, detail="Site supervisor phone is required")

        event = create_and_send_approval_event(
            db,
            tenant_id=tenant_id,
            workorder_id=wo.id,
            correlation_id=correlation_id,
            preferred_channel=preferred_channel,
        )
        return _approval_event_out(event)


@router.post("/{workorder_id}/resend-approval", response_model=ApprovalSendOut)
def resend_approval(workorder_id: str, payload: ApprovalResendIn, request: Request):
    correlation_id = get_request_correlation_id(request)
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)
    require_roles("OWNER", "SUPERVISOR")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        wo = db.execute(select(WorkOrder).where(WorkOrder.id == UUID(workorder_id))).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")
        if wo.status in {"CUSTOMER_SIGNED", "CLOSED"}:
            raise HTTPException(status_code=409, detail=f"Resend not allowed for status {wo.status}")

        event = resend_approval_link(
            db,
            tenant_id=tenant_id,
            workorder_id=wo.id,
            mode=payload.mode,
            is_reminder=False,
            correlation_id=correlation_id,
        )
        return _approval_event_out(event)


@router.post("/approval-reminders/run", response_model=ApprovalReminderRunOut)
def run_approval_reminders(request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)
    require_roles("OWNER", "SUPERVISOR")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        stats = process_due_reminders(db, tenant_id=tenant_id)
        return ApprovalReminderRunOut(
            scanned=stats.scanned,
            reminders_sent=stats.reminders_sent,
            skipped=stats.skipped,
        )


@router.post("/{workorder_id}/generate-report-async", response_model=ReportJobOut)
def generate_report_async(workorder_id: str, payload: ReportJobCreateIn, request: Request):
    correlation_id = get_request_correlation_id(request)
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)
    require_roles("OWNER", "SUPERVISOR", "TECH")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        wo = db.execute(select(WorkOrder).where(WorkOrder.id == UUID(workorder_id))).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")

        job = enqueue_report_job(
            db,
            tenant_id=tenant_id,
            workorder_id=wo.id,
            is_final=payload.is_final,
            idempotency_key=payload.idempotency_key,
            correlation_id=correlation_id,
            simulate_failures=payload.simulate_failures,
        )
        return _report_job_out(job)


@router.post("/{workorder_id}/generate-report", response_model=GenerateReportSyncOut)
def generate_report_sync(workorder_id: str, payload: ReportJobCreateIn, request: Request):
    correlation_id = get_request_correlation_id(request)
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)
    require_roles("OWNER", "SUPERVISOR", "TECH")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        wo = db.execute(select(WorkOrder).where(WorkOrder.id == UUID(workorder_id))).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="WorkOrder not found")

        job = enqueue_report_job(
            db,
            tenant_id=tenant_id,
            workorder_id=wo.id,
            is_final=payload.is_final,
            idempotency_key=payload.idempotency_key,
            correlation_id=correlation_id,
            simulate_failures=payload.simulate_failures,
        )
        result = run_report_job(db, job=job, force=True)
        status_out = "COMPLETED" if result.job.status == "SUCCEEDED" else "QUEUED_FOR_RETRY"
        return GenerateReportSyncOut(status=status_out, job=_report_job_out(result.job, result.report))


@router.get("/report-jobs/{job_id}", response_model=ReportJobOut)
def get_report_job(job_id: str, request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)
    require_roles("OWNER", "SUPERVISOR", "TECH")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        job = db.execute(select(ReportJob).where(ReportJob.id == UUID(job_id))).scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Report job not found")
        report = None
        if job.generated_report_id:
            report = db.execute(select(Report).where(Report.id == job.generated_report_id)).scalar_one_or_none()
        return _report_job_out(job, report)


@router.post("/report-jobs/{job_id}/run", response_model=ReportJobOut)
def run_report_job_endpoint(job_id: str, request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)
    require_roles("OWNER", "SUPERVISOR")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        job = db.execute(select(ReportJob).where(ReportJob.id == UUID(job_id))).scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Report job not found")

        result = run_report_job(db, job=job, force=False)
        return _report_job_out(result.job, result.report)


@router.post("/report-jobs/{job_id}/retry", response_model=ReportJobOut)
def retry_report_job_endpoint(job_id: str, request: Request):
    auth = verify_firebase_jwt(request)
    tenant_id, user_id, roles = _load_user_and_tenant(auth.firebase_uid)

    ctx_tenant_id.set(tenant_id)
    ctx_user_id.set(user_id)
    ctx_roles.set(roles)
    require_roles("OWNER", "SUPERVISOR")

    with get_app_db(tenant_id=tenant_id, user_id=user_id) as db:
        job = db.execute(select(ReportJob).where(ReportJob.id == UUID(job_id))).scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Report job not found")

        result = retry_report_job(db, job=job)
        return _report_job_out(result.job, result.report)
