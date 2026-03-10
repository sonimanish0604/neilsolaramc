from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import time

from sqlalchemy import select

from app.core.config import settings
from app.db.models.notification import (
    NotificationDeliveryJob,
    NotificationEvent,
    NotificationLog,
    NotificationTemplate,
    TenantNotificationSetting,
)
from app.db.session import get_admin_db
from app.notification_engine.recipient_resolver import resolve_recipients
from app.notification_engine.template_renderer import render_template_text

logger = logging.getLogger("notification_orchestrator")


def run_orchestrator_forever() -> None:
    logger.info("notification orchestrator started")
    while True:
        processed = process_pending_events_once()
        if processed:
            logger.info("orchestrator processed events=%s", processed)
        time.sleep(settings.notification_poll_interval_seconds)


def process_pending_events_once() -> int:
    now = datetime.now(timezone.utc)
    processed = 0

    with get_admin_db() as db:
        events = db.execute(
            select(NotificationEvent)
            .where(NotificationEvent.status.in_(["PENDING", "FAILED"]))
            .order_by(NotificationEvent.created_at.asc())
            .limit(settings.notification_batch_size)
        ).scalars().all()

        for event in events:
            if not _is_due(event.next_attempt_at, now):
                continue

            event.status = "PROCESSING"
            event.attempt_count += 1
            db.flush()

            try:
                _orchestrate_single_event(db, event)
                event.status = "PROCESSED"
                event.processed_at = now.isoformat()
                event.next_attempt_at = None
                event.last_error = None
                processed += 1
            except Exception as exc:  # noqa: BLE001
                event.status = "FAILED"
                event.last_error = str(exc)[:1000]
                event.processed_at = now.isoformat()
                if event.attempt_count < settings.notification_retry_max_attempts:
                    event.next_attempt_at = (
                        now + timedelta(seconds=settings.notification_retry_delay_seconds)
                    ).isoformat()
                logger.exception("orchestrator failed for event_id=%s", event.id)

        db.commit()

    return processed


def _orchestrate_single_event(db, event: NotificationEvent) -> None:
    setting = db.execute(
        select(TenantNotificationSetting).where(
            TenantNotificationSetting.tenant_id == event.tenant_id,
            TenantNotificationSetting.event_type == event.event_type,
            TenantNotificationSetting.enabled.is_(True),
        )
    ).scalar_one_or_none()
    if not setting:
        db.add(
            NotificationLog(
                tenant_id=event.tenant_id,
                event_id=event.id,
                channel="SYSTEM",
                recipient="-",
                status="SKIPPED",
                provider="orchestrator",
                error_message="No enabled tenant notification setting",
            )
        )
        return

    channels = setting.channels_json or event.payload_json.get("channels", [])
    recipient_roles = setting.recipient_roles_json or ["customer_site_supervisor"]
    payload = event.payload_json or {}
    template_key = setting.template_key

    jobs_created = 0
    for channel in channels:
        channel_code = str(channel).upper()
        recipients = resolve_recipients(
            channel=channel_code,
            payload=payload,
            recipient_roles=recipient_roles,
        )
        if not recipients:
            db.add(
                NotificationLog(
                    tenant_id=event.tenant_id,
                    event_id=event.id,
                    channel=channel_code,
                    recipient="-",
                    status="SKIPPED",
                    provider="orchestrator",
                    error_message="No recipients resolved",
                )
            )
            continue

        template = db.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.tenant_id == event.tenant_id,
                NotificationTemplate.template_key == template_key,
                NotificationTemplate.channel == channel_code,
                NotificationTemplate.is_active.is_(True),
            )
        ).scalar_one_or_none()

        subject_template = template.subject if template else payload.get("subject")
        body_template = template.body if template else payload.get("message", "")
        subject = render_template_text(subject_template or f"Notification: {event.event_type}", payload)
        body = render_template_text(body_template, payload)
        if channel_code == "EMAIL":
            report_url = str(payload.get("report_url") or "").strip()
            if report_url and report_url not in body:
                body = f"{body}\n\nReport PDF: {report_url}".strip()

        for recipient in recipients:
            db.add(
                NotificationDeliveryJob(
                    tenant_id=event.tenant_id,
                    notification_event_id=event.id,
                    channel=channel_code,
                    recipient=recipient,
                    subject=subject if channel_code == "EMAIL" else None,
                    body=body,
                    status="PENDING",
                )
            )
            db.add(
                NotificationLog(
                    tenant_id=event.tenant_id,
                    event_id=event.id,
                    channel=channel_code,
                    recipient=recipient,
                    status="QUEUED",
                    provider="orchestrator",
                )
            )
            jobs_created += 1

    if jobs_created == 0:
        raise RuntimeError("No delivery jobs created for event")


def _is_due(next_attempt_at: str | None, now: datetime) -> bool:
    if not next_attempt_at:
        return True
    dt = datetime.fromisoformat(next_attempt_at)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt <= now
