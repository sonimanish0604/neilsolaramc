from __future__ import annotations

import requests

from app.core.config import settings
from app.core.secrets import get_secret
from app.notification_engine.channels import ChannelDeliveryResult


def send_twilio_email(recipient: str, subject: str, body: str) -> ChannelDeliveryResult:
    """
    Twilio email path via SendGrid Mail Send API.
    Requires a SendGrid API key created under Twilio SendGrid.
    """
    if not settings.notification_twilio_email_enabled:
        return ChannelDeliveryResult(
            status="SKIPPED",
            provider="TWILIO",
            error_message="notification_twilio_email_enabled=false",
        )
    api_key = get_secret(
        logical_name="NOTIFICATION_TWILIO_SENDGRID_API_KEY",
        inline_value=settings.notification_twilio_sendgrid_api_key,
        secret_ref=settings.notification_twilio_sendgrid_api_key_secret,
    )
    if not api_key:
        return ChannelDeliveryResult(
            status="FAILED",
            provider="TWILIO",
            error_message="Twilio SendGrid API key missing",
        )

    url = "https://api.sendgrid.com/v3/mail/send"
    payload = {
        "personalizations": [{"to": [{"email": recipient}], "subject": subject}],
        "from": {"email": settings.notification_email_from},
        "content": [{"type": "text/plain", "value": body}],
    }

    try:
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=settings.notification_twilio_sendgrid_timeout_seconds,
        )
    except Exception as exc:  # noqa: BLE001
        return ChannelDeliveryResult(status="FAILED", provider="TWILIO", error_message=str(exc)[:1000])

    if resp.status_code not in (200, 202):
        return ChannelDeliveryResult(
            status="FAILED",
            provider="TWILIO",
            error_message=f"status={resp.status_code} body={resp.text[:200]}",
        )

    return ChannelDeliveryResult(status="SENT", provider="TWILIO", provider_message_id=None)
