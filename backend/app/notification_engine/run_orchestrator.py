from app.core.logging import setup_logging
from app.notification_engine.runtime import ROLE_ORCHESTRATOR, run_notification_service


def main() -> None:
    setup_logging()
    # Backward-compatible entrypoint for existing scripts.
    import os

    os.environ.setdefault("NOTIFICATION_ENGINE_ROLE", ROLE_ORCHESTRATOR)
    run_notification_service()


if __name__ == "__main__":
    main()
