from __future__ import annotations

from app.notification_engine.channels import ChannelDeliveryResult
from app.notification_engine.channels import email_adapter


def test_secondary_not_attempted_when_failover_disabled(monkeypatch):
    monkeypatch.setattr(email_adapter.settings, "notification_email_enabled", True)
    monkeypatch.setattr(email_adapter.settings, "notification_email_primary_provider", "MAILGUN")
    monkeypatch.setattr(email_adapter.settings, "notification_email_secondary_provider", "TWILIO")
    monkeypatch.setattr(email_adapter.settings, "notification_email_secondary_failover_enabled", False)

    called = {"twilio": False}

    def fake_mailgun(recipient: str, subject: str, body: str) -> ChannelDeliveryResult:
        return ChannelDeliveryResult(status="SKIPPED", provider="MAILGUN", error_message="disabled")

    def fake_twilio(recipient: str, subject: str, body: str) -> ChannelDeliveryResult:
        called["twilio"] = True
        return ChannelDeliveryResult(status="SENT", provider="TWILIO")

    monkeypatch.setattr(email_adapter, "send_mailgun_email", fake_mailgun)
    monkeypatch.setattr(email_adapter, "send_twilio_email", fake_twilio)

    result = email_adapter.send_email("to@example.com", "subject", "body")

    assert result.status == "SKIPPED"
    assert result.provider == "MAILGUN"
    assert called["twilio"] is False


def test_secondary_attempted_when_failover_enabled_and_primary_failed(monkeypatch):
    monkeypatch.setattr(email_adapter.settings, "notification_email_enabled", True)
    monkeypatch.setattr(email_adapter.settings, "notification_email_primary_provider", "MAILGUN")
    monkeypatch.setattr(email_adapter.settings, "notification_email_secondary_provider", "TWILIO")
    monkeypatch.setattr(email_adapter.settings, "notification_email_secondary_failover_enabled", True)

    def fake_mailgun(recipient: str, subject: str, body: str) -> ChannelDeliveryResult:
        return ChannelDeliveryResult(status="FAILED", provider="MAILGUN", error_message="primary failed")

    def fake_twilio(recipient: str, subject: str, body: str) -> ChannelDeliveryResult:
        return ChannelDeliveryResult(status="SENT", provider="TWILIO")

    monkeypatch.setattr(email_adapter, "send_mailgun_email", fake_mailgun)
    monkeypatch.setattr(email_adapter, "send_twilio_email", fake_twilio)

    result = email_adapter.send_email("to@example.com", "subject", "body")

    assert result.status == "SENT"
    assert result.provider == "TWILIO"
