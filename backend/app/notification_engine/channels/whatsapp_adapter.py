from __future__ import annotations

from app.core.config import settings
from app.notification_engine.channels import ChannelDeliveryResult
from app.services.whatsapp_sender import send_whatsapp_message


def send_whatsapp(recipient: str, body: str) -> ChannelDeliveryResult:
    if not settings.twilio_enabled:
        return ChannelDeliveryResult(
            status="SKIPPED",
            provider="TWILIO",
            error_message="twilio_enabled=false",
        )

    try:
        result = send_whatsapp_message(phone=recipient, message=body)
    except Exception as exc:  # noqa: BLE001
        return ChannelDeliveryResult(
            status="FAILED",
            provider="TWILIO",
            error_message=str(exc)[:1000],
        )

    return ChannelDeliveryResult(
        status="SENT",
        provider=result.provider,
        provider_message_id=result.message_id,
    )
