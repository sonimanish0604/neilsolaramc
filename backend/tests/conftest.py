from __future__ import annotations

import os


def pytest_configure() -> None:
    # Needed so app settings/session initialize during tests without real secrets.
    os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/neilsolar")
    os.environ.setdefault("DATABASE_ADMIN_URL", "postgresql+psycopg://admin:pass@localhost:5432/neilsolar")
    os.environ.setdefault("BOOTSTRAP_ADMIN_KEY", "dev-bootstrap-key")

