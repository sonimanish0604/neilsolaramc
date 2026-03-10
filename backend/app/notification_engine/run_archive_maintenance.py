from __future__ import annotations

import logging
import time

from app.core.config import settings
from app.core.logging import setup_logging
from app.notification_engine.maintenance import archive_notification_data_once

logger = logging.getLogger("notification_archive_runner")


def main() -> None:
    setup_logging()
    logger.info(
        "archive runner started run_once=%s interval_seconds=%s",
        settings.notification_maintenance_run_once,
        settings.notification_archive_interval_seconds,
    )
    while True:
        counters = archive_notification_data_once()
        logger.info(
            "archive cycle counters events_archived=%s jobs_archived=%s logs_archived=%s events_deleted=%s jobs_deleted=%s logs_deleted=%s",
            counters["events_archived"],
            counters["jobs_archived"],
            counters["logs_archived"],
            counters["events_deleted"],
            counters["jobs_deleted"],
            counters["logs_deleted"],
        )
        if settings.notification_maintenance_run_once:
            break
        time.sleep(settings.notification_archive_interval_seconds)


if __name__ == "__main__":
    main()
