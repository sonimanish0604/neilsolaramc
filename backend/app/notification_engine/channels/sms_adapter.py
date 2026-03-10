from __future__ import annotations

from app.notification_engine.channels import ChannelDeliveryResult


def send_sms(recipient: str, body: str) -> ChannelDeliveryResult:
    _ = (recipient, body)
    return ChannelDeliveryResult(
        status="SKIPPED",
        provider="SMS_STUB",
        error_message="SMS adapter not implemented yet",
    )
