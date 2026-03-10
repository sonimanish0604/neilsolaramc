from __future__ import annotations

import requests

from app.core.config import settings
from app.core.secrets import get_secret
from app.notification_engine.channels import ChannelDeliveryResult


def send_mailgun_email(recipient: str, subject: str, body: str) -> ChannelDeliveryResult:
    if not settings.notification_mailgun_enabled:
        return ChannelDeliveryResult(
            status="SKIPPED",
            provider="MAILGUN",
            error_message="notification_mailgun_enabled=false",
        )
    api_key = get_secret(
        logical_name="NOTIFICATION_MAILGUN_API_KEY",
        inline_value=settings.notification_mailgun_api_key,
        secret_ref=settings.notification_mailgun_api_key_secret,
    )
    if not settings.notification_mailgun_domain or not api_key:
        return ChannelDeliveryResult(
            status="FAILED",
            provider="MAILGUN",
            error_message="Mailgun domain/api key missing",
        )

    return send_mailgun_email_direct(
        recipient=recipient,
        subject=subject,
        body=body,
        domain=settings.notification_mailgun_domain,
        api_key=api_key,
        sender=settings.notification_email_from,
        eu_region=settings.notification_mailgun_eu_region,
        timeout_seconds=settings.notification_mailgun_timeout_seconds,
    )


def send_mailgun_email_direct(
    recipient: str,
    subject: str,
    body: str,
    *,
    domain: str,
    api_key: str,
    sender: str,
    eu_region: bool = False,
    timeout_seconds: int = 10,
    http_post=requests.post,
) -> ChannelDeliveryResult:
    base = "https://api.eu.mailgun.net" if eu_region else "https://api.mailgun.net"
    url = f"{base}/v3/{domain}/messages"
    payload = {
        "from": sender,
        "to": recipient,
        "subject": subject,
        "text": body,
    }

    try:
        resp = http_post(
            url,
            auth=("api", api_key),
            data=payload,
            timeout=timeout_seconds,
        )
    except Exception as exc:  # noqa: BLE001
        return ChannelDeliveryResult(status="FAILED", provider="MAILGUN", error_message=str(exc)[:1000])

    if resp.status_code not in (200, 202):
        return ChannelDeliveryResult(
            status="FAILED",
            provider="MAILGUN",
            error_message=f"status={resp.status_code} body={resp.text[:200]}",
        )

    try:
        data = resp.json()
        message_id = data.get("id")
    except Exception:  # noqa: BLE001
        message_id = None

    return ChannelDeliveryResult(status="SENT", provider="MAILGUN", provider_message_id=message_id)
