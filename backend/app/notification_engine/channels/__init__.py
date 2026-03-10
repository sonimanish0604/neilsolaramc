from dataclasses import dataclass


@dataclass
class ChannelDeliveryResult:
    status: str
    provider: str
    provider_message_id: str | None = None
    error_message: str | None = None
