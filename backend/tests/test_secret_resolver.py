from __future__ import annotations

from app.core import secrets


def test_env_provider_returns_inline(monkeypatch):
    monkeypatch.setattr(secrets.settings, "secret_provider", "ENV")
    value = secrets.get_secret(
        logical_name="NOTIFICATION_MAILGUN_API_KEY",
        inline_value="inline-key",
        secret_ref="ignored/path#field",
    )
    assert value == "inline-key"


def test_vault_provider_fail_open_falls_back_to_inline(monkeypatch):
    monkeypatch.setattr(secrets.settings, "secret_provider", "VAULT")
    monkeypatch.setattr(secrets.settings, "secret_fail_open", True)
    monkeypatch.setattr(secrets.settings, "vault_addr", "http://vault")
    monkeypatch.setattr(secrets.settings, "vault_token", "token")
    monkeypatch.setattr(secrets.settings, "vault_mount", "secret")
    monkeypatch.setattr(secrets.settings, "vault_kv_version", 2)
    monkeypatch.setattr(secrets.settings, "secret_cache_ttl_seconds", 0)

    def fake_get(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(secrets.requests, "get", fake_get)
    value = secrets.get_secret(
        logical_name="NOTIFICATION_MAILGUN_API_KEY",
        inline_value="inline-fallback",
        secret_ref="neilsolar/local/notification#mailgun_api_key",
    )
    assert value == "inline-fallback"


def test_vault_provider_kv2_success(monkeypatch):
    monkeypatch.setattr(secrets.settings, "secret_provider", "VAULT")
    monkeypatch.setattr(secrets.settings, "secret_fail_open", False)
    monkeypatch.setattr(secrets.settings, "vault_addr", "http://vault")
    monkeypatch.setattr(secrets.settings, "vault_token", "token")
    monkeypatch.setattr(secrets.settings, "vault_mount", "secret")
    monkeypatch.setattr(secrets.settings, "vault_kv_version", 2)
    monkeypatch.setattr(secrets.settings, "secret_cache_ttl_seconds", 0)

    class DummyResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"data": {"data": {"mailgun_api_key": "vault-key"}}}

    def fake_get(url, headers, timeout):
        assert url == "http://vault/v1/secret/data/neilsolar/local/notification"
        assert headers["X-Vault-Token"] == "token"
        assert timeout == secrets.settings.secret_fetch_timeout_seconds
        return DummyResponse()

    monkeypatch.setattr(secrets.requests, "get", fake_get)
    value = secrets.get_secret(
        logical_name="NOTIFICATION_MAILGUN_API_KEY",
        inline_value=None,
        secret_ref="neilsolar/local/notification#mailgun_api_key",
    )
    assert value == "vault-key"
