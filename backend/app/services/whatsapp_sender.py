from __future__ import annotations

from dataclasses import dataclass

import requests

from app.core.config import settings
from app.core.secrets import get_secret


@dataclass
class WhatsAppSendResult:
    provider: str
    delivery_status: str
    message_id: str | None


@dataclass
class TwilioWhatsAppConfig:
    enabled: bool
    account_sid: str | None
    auth_token: str | None
    whatsapp_from: str
    timeout_seconds: int


def _normalize_whatsapp_phone(phone: str) -> str:
    return phone if phone.startswith("whatsapp:") else f"whatsapp:{phone}"


def _build_twilio_config() -> TwilioWhatsAppConfig:
    auth_token = get_secret(
        logical_name="TWILIO_AUTH_TOKEN",
        inline_value=settings.twilio_auth_token,
        secret_ref=settings.twilio_auth_token_secret,
    )
    return TwilioWhatsAppConfig(
        enabled=settings.twilio_enabled,
        account_sid=settings.twilio_account_sid,
        auth_token=auth_token,
        whatsapp_from=settings.twilio_whatsapp_from,
        timeout_seconds=settings.twilio_request_timeout_seconds,
    )


def send_whatsapp_message(
    phone: str,
    message: str,
    config: TwilioWhatsAppConfig | None = None,
    http_post=requests.post,
) -> WhatsAppSendResult:
    cfg = config or _build_twilio_config()
    if not cfg.enabled:
        return WhatsAppSendResult(provider="TWILIO", delivery_status="SKIPPED", message_id=None)

    if not cfg.account_sid or not cfg.auth_token:
        raise RuntimeError("Twilio is enabled but credentials are not configured")

    url = f"https://api.twilio.com/2010-04-01/Accounts/{cfg.account_sid}/Messages.json"
    payload = {
        "From": _normalize_whatsapp_phone(cfg.whatsapp_from),
        "To": _normalize_whatsapp_phone(phone),
        "Body": message,
    }

    resp = http_post(
        url,
        data=payload,
        auth=(cfg.account_sid, cfg.auth_token),
        timeout=cfg.timeout_seconds,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Twilio send failed: status={resp.status_code} body={resp.text[:200]}")

    body = resp.json()
    return WhatsAppSendResult(
        provider="TWILIO",
        delivery_status=body.get("status", "queued"),
        message_id=body.get("sid"),
    )


def send_whatsapp_placeholder(phone: str, message: str) -> None:
    """
    Backward-compatible wrapper for older approval/retry code paths.
    """
    send_whatsapp_message(phone, message)
