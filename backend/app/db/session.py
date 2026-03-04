from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# APP engine (RLS enforced)
APP_ENGINE: Engine = create_engine(settings.database_url, pool_pre_ping=True)

# ADMIN engine (BYPASSRLS role) for user lookup + token resolution
ADMIN_ENGINE: Engine = create_engine(settings.database_admin_url, pool_pre_ping=True)

AppSessionLocal = sessionmaker(bind=APP_ENGINE, autocommit=False, autoflush=False)
AdminSessionLocal = sessionmaker(bind=ADMIN_ENGINE, autocommit=False, autoflush=False)


def set_rls_context(db: Session, tenant_id: UUID, user_id: Optional[UUID] = None) -> None:
    """
    Must be called inside a transaction.
    Uses SET LOCAL so it only applies to this transaction/request.
    """
    db.execute(text("SET LOCAL app.tenant_id = :tenant_id"), {"tenant_id": str(tenant_id)})
    if user_id:
        db.execute(text("SET LOCAL app.user_id = :user_id"), {"user_id": str(user_id)})


@contextmanager
def get_app_db(tenant_id: UUID, user_id: Optional[UUID] = None) -> Generator[Session, None, None]:
    db = AppSessionLocal()
    try:
        with db.begin():
            set_rls_context(db, tenant_id=tenant_id, user_id=user_id)
            yield db
    finally:
        db.close()


@contextmanager
def get_admin_db() -> Generator[Session, None, None]:
    db = AdminSessionLocal()
    try:
        yield db
    finally:
        db.close()