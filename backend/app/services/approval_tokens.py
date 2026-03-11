from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.site import Site
from app.db.models.workorder import ApprovalEvent
from app.services.email_sender import send_email_placeholder
from app.services.whatsapp_sender import send_whatsapp_placeholder


ACTIVE_APPROVAL_STATUSES = {
    "QUEUED",
    "DELIVERY_FAILED",
    "DELIVERY_PERMANENT_FAILED",
    "SENT",
    "OPENED",
}


class ApprovalDeliveryError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool):
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class DeliveryResult:
    channel: str
    recipient: str


@dataclass(frozen=True)
class ReminderStats:
    scanned: int
    reminders_sent: int
    skipped: int


@dataclass(frozen=True)
class ChannelAttemptFailure:
    channel: str
    error: str
    retryable: bool


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def generate_approval_token() -> str:
    return secrets.token_urlsafe(32)


def generate_token() -> str:
    return generate_approval_token()


def compute_expiry_iso(ttl_hours: int, now: datetime | None = None) -> str:
    base = now or now_utc()
    return iso_utc(base + timedelta(hours=ttl_hours))


def compute_expiry(ttl_hours: int | None = None) -> str:
    return compute_expiry_iso(ttl_hours or settings.approval_token_ttl_hours)


def is_expired_iso(expires_at: str, now: datetime | None = None) -> bool:
    return parse_iso(expires_at) < (now or now_utc())


def build_approval_link(token: str) -> str:
    base = (settings.approval_base_url or settings.approval_link_base_url or "").strip().rstrip("/")
    if not base:
        base = "https://app.neilsolar.com/approve"
    return f"{base}/{token}"


def compute_next_retry(attempt_count: int) -> str:
    multiplier = max(1, 2 ** max(0, attempt_count - 1))
    return iso_utc(now_utc() + timedelta(seconds=settings.approval_retry_backoff_seconds * multiplier))


def should_send_reminder(
    *,
    expires_at: str,
    reminder_count: int,
    status: str,
    max_reminders: int,
    lead_hours: int,
    now_dt: datetime | None = None,
) -> bool:
    if status not in {"SENT", "OPENED", "DELIVERY_FAILED"}:
        return False
    if reminder_count >= max_reminders:
        return False

    now_val = now_dt or now_utc()
    expiry = parse_iso(expires_at)
    return now_val <= expiry <= (now_val + timedelta(hours=lead_hours))


def classify_provider_failure(channel: str, error_message: str) -> bool:
    msg = error_message.lower()

    permanent_markers = [
        "invalid",
        "unauthorized",
        "forbidden",
        "permission denied",
        "authentication",
        "bad request",
        "recipient rejected",
        "missing recipient contact",
    ]
    if any(marker in msg for marker in permanent_markers):
        return False

    retryable_markers = [
        "timeout",
        "temporarily unavailable",
        "connection reset",
        "rate limit",
        "too many requests",
        "5xx",
        "server error",
    ]
    if any(marker in msg for marker in retryable_markers):
        return True

    return True


def _channel_attempt(
    *,
    site: Site,
    link: str,
    channel: str,
) -> DeliveryResult:
    if channel == "WHATSAPP":
        if not site.site_supervisor_phone:
            raise ApprovalDeliveryError("missing recipient contact", retryable=False)
        try:
            send_whatsapp_placeholder(site.site_supervisor_phone, f"Approval link: {link}")
            return DeliveryResult(channel="WHATSAPP", recipient=site.site_supervisor_phone)
        except Exception as exc:  # pragma: no cover
            err = str(exc)
            raise ApprovalDeliveryError(err, retryable=classify_provider_failure("WHATSAPP", err)) from exc

    if channel == "EMAIL":
        if not site.site_supervisor_email:
            raise ApprovalDeliveryError("missing recipient contact", retryable=False)
        try:
            send_email_placeholder(
                site.site_supervisor_email,
                "AMC approval link",
                f"Please review and sign: {link}",
            )
            return DeliveryResult(channel="EMAIL", recipient=site.site_supervisor_email)
        except Exception as exc:  # pragma: no cover
            err = str(exc)
            raise ApprovalDeliveryError(err, retryable=classify_provider_failure("EMAIL", err)) from exc

    raise ApprovalDeliveryError(f"unsupported channel {channel}", retryable=False)


def _deliver_link(site: Site, link: str, preferred_channel: str | None = None) -> DeliveryResult:
    if preferred_channel:
        return _channel_attempt(site=site, link=link, channel=preferred_channel)

    failures: list[ChannelAttemptFailure] = []
    for channel in ("WHATSAPP", "EMAIL"):
        try:
            return _channel_attempt(site=site, link=link, channel=channel)
        except ApprovalDeliveryError as exc:
            failures.append(
                ChannelAttemptFailure(channel=channel, error=str(exc), retryable=exc.retryable)
            )

    if not failures:
        raise ApprovalDeliveryError("missing recipient contact", retryable=False)

    message = "; ".join(f"{f.channel.lower()}:{f.error}" for f in failures)
    retryable = any(f.retryable for f in failures)
    raise ApprovalDeliveryError(message, retryable=retryable)


def _load_site_for_workorder(db: Session, workorder_id: UUID) -> Site | None:
    from app.db.models.workorder import WorkOrder

    workorder = db.execute(select(WorkOrder).where(WorkOrder.id == workorder_id)).scalar_one_or_none()
    if not workorder:
        return None
    return db.execute(select(Site).where(Site.id == workorder.site_id)).scalar_one_or_none()


def create_and_send_approval_event(
    db: Session,
    *,
    tenant_id: UUID,
    workorder_id: UUID,
    reminder_count: int = 0,
    correlation_id: str | None = None,
    preferred_channel: str | None = None,
) -> ApprovalEvent:
    site = _load_site_for_workorder(db, workorder_id)
    if not site:
        raise ValueError("Site not found for workorder")

    chosen_channel = preferred_channel or ("WHATSAPP" if site.site_supervisor_phone else "EMAIL")
    event = ApprovalEvent(
        tenant_id=tenant_id,
        workorder_id=workorder_id,
        token=generate_approval_token(),
        correlation_id=correlation_id,
        channel=chosen_channel,
        expires_at=compute_expiry(),
        status="QUEUED",
        attempt_count=0,
        reminder_count=reminder_count,
    )

    db.add(event)
    db.flush()

    if reminder_count > 0:
        event.last_reminder_at = iso_utc(now_utc())

    _attempt_send(db, event, site, preferred_channel=chosen_channel)
    return event


def _attempt_send(db: Session, event: ApprovalEvent, site: Site, *, preferred_channel: str | None = None) -> None:
    link = build_approval_link(event.token)
    event.attempt_count += 1

    try:
        delivery = _deliver_link(site, link, preferred_channel or event.channel)
        event.channel = delivery.channel
        event.recipient = delivery.recipient
        event.status = "SENT"
        event.sent_at = iso_utc(now_utc())
        event.last_error = None
        event.next_retry_at = None
    except ApprovalDeliveryError as exc:
        event.status = "DELIVERY_FAILED" if exc.retryable else "DELIVERY_PERMANENT_FAILED"
        event.last_error = str(exc)[:1000]
        if not exc.retryable or event.attempt_count >= settings.approval_retry_max_attempts:
            event.next_retry_at = None
        else:
            event.next_retry_at = compute_next_retry(event.attempt_count)

    db.flush()


def retry_delivery_if_due(db: Session, event: ApprovalEvent) -> bool:
    if event.status != "DELIVERY_FAILED":
        return False
    if event.attempt_count >= settings.approval_retry_max_attempts:
        return False
    if event.next_retry_at and parse_iso(event.next_retry_at) > now_utc():
        return False

    site = _load_site_for_workorder(db, event.workorder_id)
    if not site:
        event.last_error = "site missing for workorder"
        return False

    _attempt_send(db, event, site, preferred_channel=event.channel)
    return event.status == "SENT"


def latest_active_event(db: Session, workorder_id: UUID) -> ApprovalEvent | None:
    stmt = (
        select(ApprovalEvent)
        .where(ApprovalEvent.workorder_id == workorder_id, ApprovalEvent.status.in_(ACTIVE_APPROVAL_STATUSES))
        .order_by(ApprovalEvent.created_at.desc())
    )
    return db.execute(stmt).scalars().first()


def supersede_event(event: ApprovalEvent, new_event_id: UUID | None = None) -> None:
    event.status = "SUPERSEDED"
    event.superseded_by_event_id = new_event_id
    event.next_retry_at = None


def resend_approval_link(
    db: Session,
    *,
    tenant_id: UUID,
    workorder_id: UUID,
    mode: str,
    is_reminder: bool = False,
    correlation_id: str | None = None,
) -> ApprovalEvent:
    current = latest_active_event(db, workorder_id)

    if mode == "EXTEND" and current:
        site = _load_site_for_workorder(db, workorder_id)
        if not site:
            raise ValueError("Site not found for workorder")

        current.expires_at = compute_expiry()
        current.reminder_count = current.reminder_count + (1 if is_reminder else 0)
        current.last_reminder_at = iso_utc(now_utc()) if is_reminder else current.last_reminder_at
        _attempt_send(db, current, site, preferred_channel=current.channel)
        return current

    if current:
        supersede_event(current)

    event = create_and_send_approval_event(
        db,
        tenant_id=tenant_id,
        workorder_id=workorder_id,
        reminder_count=(current.reminder_count + 1) if (is_reminder and current) else 0,
        correlation_id=correlation_id,
        preferred_channel=current.channel if current else None,
    )
    if current:
        current.superseded_by_event_id = event.id
    return event


def process_due_reminders(db: Session, tenant_id: UUID) -> ReminderStats:
    now_val = now_utc()
    stmt = (
        select(ApprovalEvent)
        .where(
            ApprovalEvent.tenant_id == tenant_id,
            ApprovalEvent.status.in_(["SENT", "OPENED", "DELIVERY_FAILED", "DELIVERY_PERMANENT_FAILED"]),
        )
        .order_by(ApprovalEvent.created_at.asc())
    )

    scanned = 0
    reminders_sent = 0
    skipped = 0

    for event in db.execute(stmt).scalars().all():
        scanned += 1

        if parse_iso(event.expires_at) < now_val:
            event.status = "EXPIRED"
            skipped += 1
            continue

        if not should_send_reminder(
            expires_at=event.expires_at,
            reminder_count=event.reminder_count,
            status=event.status,
            max_reminders=settings.approval_max_reminders,
            lead_hours=settings.approval_reminder_lead_hours,
            now_dt=now_val,
        ):
            if event.status == "DELIVERY_FAILED":
                retry_delivery_if_due(db, event)
            skipped += 1
            continue

        resend_approval_link(
            db,
            tenant_id=tenant_id,
            workorder_id=event.workorder_id,
            mode="NEW_TOKEN",
            is_reminder=True,
            correlation_id=event.correlation_id,
        )
        reminders_sent += 1

    return ReminderStats(scanned=scanned, reminders_sent=reminders_sent, skipped=skipped)
