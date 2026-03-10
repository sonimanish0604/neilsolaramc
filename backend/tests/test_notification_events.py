from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.workorders import SendApprovalIn


def test_send_approval_channel_supports_email_and_whatsapp():
    assert SendApprovalIn(channel="WHATSAPP").channel == "WHATSAPP"
    assert SendApprovalIn(channel="EMAIL").channel == "EMAIL"


def test_send_approval_channel_rejects_unknown():
    with pytest.raises(ValidationError):
        SendApprovalIn(channel="SMS")


def test_notification_event_payload_shape():
    payload = {
        "approval_token": "tok_123",
        "approval_url": "https://app.neilsolar.com/approve/tok_123",
        "expires_at": "2026-03-10T12:00:00+00:00",
        "channels": ["WHATSAPP"],
        "site_name": "Demo Site",
        "site_supervisor_phone": "+919999999999",
        "message": "demo message",
        "workorder_id": str(uuid4()),
        "tenant_id": str(uuid4()),
    }
    assert payload["channels"] == ["WHATSAPP"]
