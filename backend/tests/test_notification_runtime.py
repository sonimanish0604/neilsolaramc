from __future__ import annotations

import os

from app.notification_engine import runtime


def test_resolve_role_defaults_to_orchestrator(monkeypatch):
    monkeypatch.delenv("NOTIFICATION_ENGINE_ROLE", raising=False)
    monkeypatch.delenv("NOTIF_WORKER_CHANNEL", raising=False)
    assert runtime._resolve_role() == runtime.ROLE_ORCHESTRATOR


def test_resolve_role_uses_worker_channel_backcompat(monkeypatch):
    monkeypatch.delenv("NOTIFICATION_ENGINE_ROLE", raising=False)
    monkeypatch.setenv("NOTIF_WORKER_CHANNEL", "whatsapp")
    assert runtime._resolve_role() == runtime.ROLE_WORKER_WHATSAPP


def test_run_once_orchestrator(monkeypatch):
    monkeypatch.setenv("NOTIFICATION_ENGINE_ROLE", runtime.ROLE_ORCHESTRATOR)
    monkeypatch.setenv("NOTIFICATION_ENGINE_RUN_ONCE", "true")

    called = {"once": False}

    def fake_once():
        called["once"] = True
        return 3

    monkeypatch.setattr(runtime, "process_pending_events_once", fake_once)
    monkeypatch.setattr(runtime, "run_orchestrator_forever", lambda: (_ for _ in ()).throw(RuntimeError("bad")))

    runtime.run_notification_service()
    assert called["once"] is True


def test_run_once_worker_email(monkeypatch):
    monkeypatch.setenv("NOTIFICATION_ENGINE_ROLE", runtime.ROLE_WORKER_EMAIL)
    monkeypatch.setenv("NOTIFICATION_ENGINE_RUN_ONCE", "1")

    observed: dict[str, str] = {}

    def fake_process_channel_jobs_once(channel: str) -> int:
        observed["channel"] = channel
        return 1

    monkeypatch.setattr(runtime, "process_channel_jobs_once", fake_process_channel_jobs_once)
    monkeypatch.setattr(
        runtime,
        "run_channel_worker_forever",
        lambda channel: (_ for _ in ()).throw(RuntimeError(f"bad {channel}")),
    )

    runtime.run_notification_service()
    assert observed["channel"] == "EMAIL"


def test_read_bool_variants():
    os.environ["NOTIFICATION_ENGINE_RUN_ONCE"] = "Yes"
    assert runtime._read_bool("NOTIFICATION_ENGINE_RUN_ONCE", default=False)
    os.environ["NOTIFICATION_ENGINE_RUN_ONCE"] = "0"
    assert not runtime._read_bool("NOTIFICATION_ENGINE_RUN_ONCE", default=True)
