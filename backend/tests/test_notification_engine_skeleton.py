from __future__ import annotations

from app.notification_engine.recipient_resolver import resolve_recipients
from app.notification_engine.template_renderer import render_template_text


def test_template_renderer_replaces_variables():
    text = render_template_text(
        "Hello {{name}}, WO {{workorder_id}} is {{status}}",
        {"name": "Manish", "workorder_id": "wo-1", "status": "queued"},
    )
    assert text == "Hello Manish, WO wo-1 is queued"


def test_recipient_resolver_email_uses_payload():
    recipients = resolve_recipients(
        channel="EMAIL",
        payload={"site_supervisor_email": "site@example.com"},
        recipient_roles=["customer_site_supervisor"],
    )
    assert recipients == ["site@example.com"]


def test_recipient_resolver_whatsapp_payload():
    recipients = resolve_recipients(
        channel="WHATSAPP",
        payload={"site_supervisor_phone": "+919999999999"},
        recipient_roles=["customer_site_supervisor"],
    )
    assert recipients == ["+919999999999"]
