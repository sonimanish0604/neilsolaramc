from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import time

from sqlalchemy import select

from app.core.config import settings
from app.db.models.notification import NotificationDeliveryJob, NotificationLog
from app.db.session import get_admin_db
from app.notification_engine.channels import ChannelDeliveryResult
from app.notification_engine.channels.email_adapter import send_email
from app.notification_engine.channels.sms_adapter import send_sms
from app.notification_engine.channels.whatsapp_adapter import send_whatsapp

logger = logging.getLogger("notification_channel_worker")


def run_channel_worker_forever(channel: str) -> None:
    channel_code = channel.upper()
    logger.info("channel worker started channel=%s", channel_code)
    while True:
        processed = process_channel_jobs_once(channel_code)
        if processed:
            logger.info("channel worker processed channel=%s jobs=%s", channel_code, processed)
        time.sleep(settings.notification_poll_interval_seconds)


def process_channel_jobs_once(channel: str) -> int:
    now = datetime.now(timezone.utc)
    processed = 0

    with get_admin_db() as db:
        jobs = db.execute(
            select(NotificationDeliveryJob)
            .where(
                NotificationDeliveryJob.channel == channel,
                NotificationDeliveryJob.status.in_(["PENDING", "FAILED"]),
                NotificationDeliveryJob.attempt_count < settings.notification_retry_max_attempts,
            )
            .order_by(NotificationDeliveryJob.created_at.asc())
            .limit(settings.notification_batch_size)
        ).scalars().all()

        for job in jobs:
            if not _is_due(job.next_attempt_at, now):
                continue

            job.status = "PROCESSING"
            db.flush()

            result = _dispatch(
                channel=channel,
                recipient=job.recipient,
                subject=job.subject or f"Notification: {channel}",
                body=job.body,
            )
            job.attempt_count += 1

            if result.status in {"SENT", "SKIPPED"}:
                job.status = result.status
                job.processed_at = now.isoformat()
                job.last_error = result.error_message
                job.next_attempt_at = None
            else:
                job.status = "FAILED"
                job.last_error = result.error_message
                if job.attempt_count < settings.notification_retry_max_attempts:
                    job.next_attempt_at = (
                        now + timedelta(seconds=settings.notification_retry_delay_seconds)
                    ).isoformat()

            db.add(
                NotificationLog(
                    tenant_id=job.tenant_id,
                    event_id=job.notification_event_id,
                    channel=channel,
                    recipient=job.recipient,
                    status=job.status,
                    provider=result.provider,
                    provider_message_id=result.provider_message_id,
                    error_message=result.error_message,
                    sent_at=now.isoformat() if job.status == "SENT" else None,
                )
            )
            processed += 1

        db.commit()

    return processed


def _dispatch(channel: str, recipient: str, subject: str, body: str) -> ChannelDeliveryResult:
    if channel == "EMAIL":
        return send_email(recipient=recipient, subject=subject, body=body)
    if channel == "WHATSAPP":
        return send_whatsapp(recipient=recipient, body=body)
    if channel == "SMS":
        return send_sms(recipient=recipient, body=body)
    return ChannelDeliveryResult(
        status="FAILED",
        provider="UNKNOWN",
        error_message=f"Unsupported channel: {channel}",
    )


def _is_due(next_attempt_at: str | None, now: datetime) -> bool:
    if not next_attempt_at:
        return True
    dt = datetime.fromisoformat(next_attempt_at)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt <= now
