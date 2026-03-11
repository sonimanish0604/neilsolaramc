from app.core.logging import setup_logging
from app.notification_engine.runtime import run_notification_service


def main() -> None:
    setup_logging()
    run_notification_service()


if __name__ == "__main__":
    main()
