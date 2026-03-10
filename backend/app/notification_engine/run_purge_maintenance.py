from __future__ import annotations

import logging
import time

from app.core.config import settings
from app.core.logging import setup_logging
from app.notification_engine.maintenance import purge_notification_history_once

logger = logging.getLogger("notification_purge_runner")


def main() -> None:
    setup_logging()
    logger.info(
        "purge runner started run_once=%s interval_seconds=%s",
        settings.notification_maintenance_run_once,
        settings.notification_purge_interval_seconds,
    )
    while True:
        counters = purge_notification_history_once()
        logger.info(
            "purge cycle counters events_purged=%s jobs_purged=%s logs_purged=%s",
            counters["events_purged"],
            counters["jobs_purged"],
            counters["logs_purged"],
        )
        if settings.notification_maintenance_run_once:
            break
        time.sleep(settings.notification_purge_interval_seconds)


if __name__ == "__main__":
    main()
