from __future__ import annotations

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.core.config import settings
from app.db.models.base import Base

# import models so Alembic sees them
from app.db.models.tenant import Tenant  # noqa
from app.db.models.user import User, UserRole  # noqa
from app.db.models.site import Customer, Site  # noqa
from app.db.models.workorder import (  # noqa
    WorkOrder, ChecklistResponse, NetMeterReading, InverterReading,
    Media, Signature, Report, ReportJob, ApprovalEvent
)
from app.db.models.notification import (  # noqa
    NotificationEvent, TenantNotificationSetting, NotificationTemplate, NotificationLog,
    NotificationDeliveryJob
)

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = settings.database_admin_url  # use admin for migrations
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = settings.database_admin_url

    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
