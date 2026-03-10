from __future__ import annotations

import logging
import os

from app.notification_engine.channel_worker import (
    process_channel_jobs_once,
    run_channel_worker_forever,
)
from app.notification_engine.orchestrator import (
    process_pending_events_once,
    run_orchestrator_forever,
)

logger = logging.getLogger("notification_runtime")

ROLE_ORCHESTRATOR = "ORCHESTRATOR"
ROLE_WORKER_EMAIL = "WORKER_EMAIL"
ROLE_WORKER_WHATSAPP = "WORKER_WHATSAPP"
ROLE_WORKER_SMS = "WORKER_SMS"


def run_notification_service() -> None:
    role = _resolve_role()
    run_once = _read_bool("NOTIFICATION_ENGINE_RUN_ONCE", default=False)

    logger.info("notification runtime started role=%s run_once=%s", role, run_once)

    if role == ROLE_ORCHESTRATOR:
        _run_orchestrator(run_once=run_once)
        return
    if role == ROLE_WORKER_EMAIL:
        _run_worker(channel="EMAIL", run_once=run_once)
        return
    if role == ROLE_WORKER_WHATSAPP:
        _run_worker(channel="WHATSAPP", run_once=run_once)
        return
    if role == ROLE_WORKER_SMS:
        _run_worker(channel="SMS", run_once=run_once)
        return
    raise RuntimeError(
        f"Unsupported NOTIFICATION_ENGINE_ROLE: {role}. "
        f"Use one of: {ROLE_ORCHESTRATOR}, {ROLE_WORKER_EMAIL}, {ROLE_WORKER_WHATSAPP}, {ROLE_WORKER_SMS}"
    )


def _run_orchestrator(*, run_once: bool) -> None:
    if run_once:
        processed = process_pending_events_once()
        logger.info("notification runtime run_once role=%s processed=%s", ROLE_ORCHESTRATOR, processed)
        return
    run_orchestrator_forever()


def _run_worker(*, channel: str, run_once: bool) -> None:
    if run_once:
        processed = process_channel_jobs_once(channel=channel)
        logger.info("notification runtime run_once role=WORKER_%s processed=%s", channel, processed)
        return
    run_channel_worker_forever(channel=channel)


def _resolve_role() -> str:
    explicit = os.getenv("NOTIFICATION_ENGINE_ROLE", "").strip().upper()
    if explicit:
        return explicit

    # Backward compatibility with existing worker env.
    notif_worker_channel = os.getenv("NOTIF_WORKER_CHANNEL", "").strip().upper()
    if notif_worker_channel == "EMAIL":
        return ROLE_WORKER_EMAIL
    if notif_worker_channel == "WHATSAPP":
        return ROLE_WORKER_WHATSAPP
    if notif_worker_channel == "SMS":
        return ROLE_WORKER_SMS

    return ROLE_ORCHESTRATOR


def _read_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "t", "yes", "y", "on"}
