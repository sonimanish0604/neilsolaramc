from __future__ import annotations

from pydantic import BaseModel, Field


class TrySendEmailIn(BaseModel):
    to: str = Field(min_length=3, max_length=320)
    subject: str = Field(default="Mailgun test email", min_length=1, max_length=500)
    text: str = Field(default="Mailgun test message", min_length=1, max_length=5000)
    domain_selector: int = Field(default=1, ge=1, le=2)
    from_email: str | None = Field(default=None, max_length=320)
    mailgun_domain: str | None = Field(default=None, max_length=255)
    mailgun_api_key: str | None = Field(default=None, max_length=255)
    mailgun_eu_region: bool | None = None


class TrySendEmailOut(BaseModel):
    status: str
    provider: str
    provider_message_id: str | None = None
    detail: str | None = None
    used_domain_selector: int
    used_domain: str
    used_from: str
