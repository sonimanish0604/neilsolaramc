from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.approval_tokens import compute_expiry_iso, generate_approval_token, is_expired_iso
from app.services.report_generator import ReportRenderContext, generate_report_placeholder
from app.services.whatsapp_sender import TwilioWhatsAppConfig, send_whatsapp_message


def test_generate_approval_token_entropy_batch():
    tokens = {generate_approval_token() for _ in range(500)}
    assert len(tokens) == 500


def test_compute_expiry_iso_72h_policy():
    base = datetime(2026, 3, 7, 12, 0, 0, tzinfo=timezone.utc)
    expires = compute_expiry_iso(72, now=base)
    assert expires == "2026-03-10T12:00:00+00:00"


def test_is_expired_iso_handles_utc():
    now = datetime(2026, 3, 7, 12, 0, 0, tzinfo=timezone.utc)
    assert is_expired_iso("2026-03-07T11:59:59+00:00", now=now)
    assert not is_expired_iso("2026-03-07T12:00:01+00:00", now=now)


def test_report_generation_changes_hash_for_customer_signed_variant():
    tech = generate_report_placeholder(
        "wo-1",
        context=ReportRenderContext(
            brand_label="NEIL",
            site_name="Site A",
            visit_status="SATISFACTORY",
            include_customer_signature=False,
        ),
    )
    final = generate_report_placeholder(
        "wo-1",
        context=ReportRenderContext(
            brand_label="NEIL",
            site_name="Site A",
            visit_status="SATISFACTORY",
            include_customer_signature=True,
        ),
    )
    assert tech.sha256 != final.sha256


def test_whatsapp_sender_skips_when_disabled():
    cfg = TwilioWhatsAppConfig(
        enabled=False,
        account_sid=None,
        auth_token=None,
        whatsapp_from="whatsapp:+14155238886",
        timeout_seconds=5,
    )
    result = send_whatsapp_message("+919999999999", "test", config=cfg)
    assert result.delivery_status == "SKIPPED"


def test_whatsapp_sender_success():
    class DummyResponse:
        status_code = 201

        @staticmethod
        def json():
            return {"sid": "SM123", "status": "queued"}

    def fake_post(url, data, auth, timeout):
        assert "/Messages.json" in url
        assert data["From"].startswith("whatsapp:")
        assert data["To"].startswith("whatsapp:")
        assert auth == ("AC123", "tok123")
        assert timeout == 5
        return DummyResponse()

    cfg = TwilioWhatsAppConfig(
        enabled=True,
        account_sid="AC123",
        auth_token="tok123",
        whatsapp_from="whatsapp:+14155238886",
        timeout_seconds=5,
    )
    result = send_whatsapp_message("+919999999999", "test", config=cfg, http_post=fake_post)
    assert result.message_id == "SM123"
    assert result.delivery_status == "queued"


def test_whatsapp_sender_raises_on_provider_failure():
    class DummyResponse:
        status_code = 400
        text = "bad request"

        @staticmethod
        def json():
            return {}

    def fake_post(url, data, auth, timeout):
        return DummyResponse()

    cfg = TwilioWhatsAppConfig(
        enabled=True,
        account_sid="AC123",
        auth_token="tok123",
        whatsapp_from="whatsapp:+14155238886",
        timeout_seconds=5,
    )
    with pytest.raises(RuntimeError):
        send_whatsapp_message("+919999999999", "test", config=cfg, http_post=fake_post)
