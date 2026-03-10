from __future__ import annotations

import os

from app.core.logging import setup_logging
from app.notification_engine.runtime import (
    ROLE_WORKER_EMAIL,
    ROLE_WORKER_SMS,
    ROLE_WORKER_WHATSAPP,
    run_notification_service,
)


def main() -> None:
    setup_logging()
    channel = os.getenv("NOTIF_WORKER_CHANNEL", "EMAIL").upper()
    # Backward-compatible entrypoint for existing scripts.
    if channel == "WHATSAPP":
        os.environ.setdefault("NOTIFICATION_ENGINE_ROLE", ROLE_WORKER_WHATSAPP)
    elif channel == "SMS":
        os.environ.setdefault("NOTIFICATION_ENGINE_ROLE", ROLE_WORKER_SMS)
    else:
        os.environ.setdefault("NOTIFICATION_ENGINE_ROLE", ROLE_WORKER_EMAIL)
    run_notification_service()


if __name__ == "__main__":
    main()
