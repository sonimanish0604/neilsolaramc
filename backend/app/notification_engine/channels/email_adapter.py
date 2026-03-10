from __future__ import annotations

from datetime import datetime, timezone
from email.message import EmailMessage
import smtplib
import uuid

from app.core.config import settings
from app.core.secrets import get_secret
from app.notification_engine.channels import ChannelDeliveryResult
from app.notification_engine.channels.mailgun_adapter import send_mailgun_email
from app.notification_engine.channels.twilio_email_adapter import send_twilio_email


def send_email(recipient: str, subject: str, body: str) -> ChannelDeliveryResult:
    if not settings.notification_email_enabled:
        return ChannelDeliveryResult(
            status="SKIPPED",
            provider="EMAIL_STUB",
            provider_message_id=f"stub-{uuid.uuid4()}",
            error_message="notification_email_enabled=false",
        )

    primary = _normalize_provider(settings.notification_email_primary_provider)
    secondary = _normalize_provider(settings.notification_email_secondary_provider)

    if not primary:
        return ChannelDeliveryResult(
            status="FAILED",
            provider="EMAIL",
            error_message="No primary email provider configured",
        )

    primary_result = _send_with_provider(provider=primary, recipient=recipient, subject=subject, body=body)
    if primary_result.status in {"SENT", "SKIPPED"}:
        return primary_result

    if not settings.notification_email_secondary_failover_enabled:
        return primary_result
    if not secondary or secondary == primary:
        return primary_result

    return _send_with_provider(provider=secondary, recipient=recipient, subject=subject, body=body)


def _send_with_provider(provider: str, recipient: str, subject: str, body: str) -> ChannelDeliveryResult:
    if provider == "MAILGUN":
        return send_mailgun_email(recipient=recipient, subject=subject, body=body)
    if provider == "TWILIO":
        return send_twilio_email(recipient=recipient, subject=subject, body=body)
    if provider == "SMTP":
        return _send_smtp_email(recipient=recipient, subject=subject, body=body)
    return ChannelDeliveryResult(
        status="FAILED",
        provider=provider,
        error_message=f"Unknown email provider: {provider}",
    )


def _send_smtp_email(recipient: str, subject: str, body: str) -> ChannelDeliveryResult:
    smtp_password = get_secret(
        logical_name="NOTIFICATION_EMAIL_SMTP_PASSWORD",
        inline_value=settings.notification_email_smtp_password,
        secret_ref=settings.notification_email_smtp_password_secret,
    )
    if not settings.notification_email_smtp_user or not smtp_password:
        return ChannelDeliveryResult(status="FAILED", provider="SMTP", error_message="SMTP credentials missing")

    msg = EmailMessage()
    msg["From"] = settings.notification_email_from
    msg["To"] = recipient
    msg["Subject"] = subject
    msg["Message-ID"] = f"<{uuid.uuid4()}@neilsolar.local>"
    msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    msg.set_content(body)

    try:
        smtp_cls = smtplib.SMTP_SSL if settings.notification_email_smtp_ssl else smtplib.SMTP
        with smtp_cls(
            settings.notification_email_smtp_host,
            settings.notification_email_smtp_port,
            timeout=10,
        ) as smtp:
            smtp.ehlo()
            if settings.notification_email_smtp_starttls and not settings.notification_email_smtp_ssl:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(settings.notification_email_smtp_user, smtp_password)
            smtp.send_message(msg)
    except Exception as exc:  # noqa: BLE001
        return ChannelDeliveryResult(
            status="FAILED",
            provider="SMTP",
            error_message=str(exc)[:1000],
        )

    return ChannelDeliveryResult(
        status="SENT",
        provider="SMTP",
        provider_message_id=msg["Message-ID"],
    )


def _normalize_provider(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().upper()
