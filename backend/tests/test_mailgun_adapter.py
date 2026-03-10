from __future__ import annotations

from app.notification_engine.channels.mailgun_adapter import send_mailgun_email_direct
from app.schemas.notifications import TrySendEmailIn


def test_send_mailgun_email_direct_success():
    class DummyResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"id": "<20260309.1@test.mailgun.org>"}

    def fake_post(url, auth, data, timeout):
        assert url == "https://api.mailgun.net/v3/sandbox.example.mailgun.org/messages"
        assert auth == ("api", "key-test")
        assert data["from"] == "postmaster@sandbox.example.mailgun.org"
        assert data["to"] == "receiver@example.com"
        assert timeout == 7
        return DummyResponse()

    result = send_mailgun_email_direct(
        recipient="receiver@example.com",
        subject="hello",
        body="world",
        domain="sandbox.example.mailgun.org",
        api_key="key-test",
        sender="postmaster@sandbox.example.mailgun.org",
        timeout_seconds=7,
        http_post=fake_post,
    )
    assert result.status == "SENT"
    assert result.provider == "MAILGUN"
    assert result.provider_message_id == "<20260309.1@test.mailgun.org>"


def test_send_mailgun_email_direct_provider_error():
    class DummyResponse:
        status_code = 401
        text = "forbidden"

        @staticmethod
        def json():
            return {}

    def fake_post(url, auth, data, timeout):
        return DummyResponse()

    result = send_mailgun_email_direct(
        recipient="receiver@example.com",
        subject="hello",
        body="world",
        domain="sandbox.example.mailgun.org",
        api_key="bad-key",
        sender="postmaster@sandbox.example.mailgun.org",
        http_post=fake_post,
    )
    assert result.status == "FAILED"
    assert result.provider == "MAILGUN"
    assert "status=401" in (result.error_message or "")


def test_trysendemail_domain_selector_defaults_to_primary():
    payload = TrySendEmailIn(to="receiver@example.com")
    assert payload.domain_selector == 1
