from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_admin_db

logger = logging.getLogger("notification_maintenance")


@dataclass
class TenantRetentionContext:
    tenant_id: str
    tenant_status: str
    tenant_updated_at: datetime
    active_retention_days: int
    notification_history_retention_days: int
    dead_letter_retention_days: int
    purge_after_deactivation_days: int
    archive_enabled: bool
    purge_enabled: bool


def archive_notification_data_once(now: datetime | None = None) -> dict[str, int]:
    current = now or datetime.now(timezone.utc)
    counters = _new_counter()

    with get_admin_db() as db:
        contexts = _load_tenant_contexts(db)
        for ctx in contexts:
            if not ctx.archive_enabled:
                continue

            cutoff = current - timedelta(days=ctx.active_retention_days)
            params = {
                "tenant_id": ctx.tenant_id,
                "cutoff": cutoff,
                "now": current,
                "max_attempts": settings.notification_retry_max_attempts,
            }

            counters["events_archived"] += _execute(
                db,
                """
                INSERT INTO notification_events_history
                (tenant_id,id,created_at,updated_at,event_type,entity_type,entity_id,payload_json,status,attempt_count,next_attempt_at,processed_at,last_error,archived_at)
                SELECT tenant_id,id,created_at,updated_at,event_type,entity_type,entity_id,payload_json,status,attempt_count,next_attempt_at,processed_at,last_error,:now
                FROM notification_events
                WHERE tenant_id = :tenant_id
                  AND created_at < :cutoff
                  AND (status = 'PROCESSED' OR (status = 'FAILED' AND attempt_count >= :max_attempts))
                ON CONFLICT (id) DO NOTHING
                """,
                params,
            )
            counters["jobs_archived"] += _execute(
                db,
                """
                INSERT INTO notification_delivery_jobs_history
                (tenant_id,id,created_at,updated_at,notification_event_id,channel,recipient,subject,body,status,attempt_count,next_attempt_at,processed_at,last_error,archived_at)
                SELECT tenant_id,id,created_at,updated_at,notification_event_id,channel,recipient,subject,body,status,attempt_count,next_attempt_at,processed_at,last_error,:now
                FROM notification_delivery_jobs
                WHERE tenant_id = :tenant_id
                  AND created_at < :cutoff
                  AND (
                        status IN ('SENT','SKIPPED')
                        OR (status = 'FAILED' AND attempt_count >= :max_attempts)
                      )
                ON CONFLICT (id) DO NOTHING
                """,
                params,
            )
            counters["logs_archived"] += _execute(
                db,
                """
                INSERT INTO notification_logs_history
                (tenant_id,id,created_at,updated_at,event_id,channel,recipient,status,provider,provider_message_id,error_message,sent_at,archived_at)
                SELECT tenant_id,id,created_at,updated_at,event_id,channel,recipient,status,provider,provider_message_id,error_message,sent_at,:now
                FROM notification_logs
                WHERE tenant_id = :tenant_id
                  AND created_at < :cutoff
                ON CONFLICT (id) DO NOTHING
                """,
                params,
            )

            counters["events_deleted"] += _execute(
                db,
                """
                DELETE FROM notification_events e
                USING notification_events_history h
                WHERE e.id = h.id
                  AND e.tenant_id = :tenant_id
                  AND h.tenant_id = :tenant_id
                """,
                params,
            )
            counters["jobs_deleted"] += _execute(
                db,
                """
                DELETE FROM notification_delivery_jobs j
                USING notification_delivery_jobs_history h
                WHERE j.id = h.id
                  AND j.tenant_id = :tenant_id
                  AND h.tenant_id = :tenant_id
                """,
                params,
            )
            counters["logs_deleted"] += _execute(
                db,
                """
                DELETE FROM notification_logs l
                USING notification_logs_history h
                WHERE l.id = h.id
                  AND l.tenant_id = :tenant_id
                  AND h.tenant_id = :tenant_id
                """,
                params,
            )

        db.commit()

    return counters


def purge_notification_history_once(now: datetime | None = None) -> dict[str, int]:
    current = now or datetime.now(timezone.utc)
    counters = _new_counter()

    with get_admin_db() as db:
        contexts = _load_tenant_contexts(db)
        for ctx in contexts:
            if not ctx.purge_enabled:
                continue

            if _is_tenant_deactivated_and_purgeable(ctx, current):
                params = {"tenant_id": ctx.tenant_id}
                counters["events_purged"] += _execute(
                    db,
                    "DELETE FROM notification_events_history WHERE tenant_id = :tenant_id",
                    params,
                )
                counters["jobs_purged"] += _execute(
                    db,
                    "DELETE FROM notification_delivery_jobs_history WHERE tenant_id = :tenant_id",
                    params,
                )
                counters["logs_purged"] += _execute(
                    db,
                    "DELETE FROM notification_logs_history WHERE tenant_id = :tenant_id",
                    params,
                )
                continue

            history_cutoff = current - timedelta(days=ctx.notification_history_retention_days)
            dead_letter_cutoff = current - timedelta(days=ctx.dead_letter_retention_days)
            params = {
                "tenant_id": ctx.tenant_id,
                "history_cutoff": history_cutoff,
                "dead_letter_cutoff": dead_letter_cutoff,
            }
            counters["events_purged"] += _execute(
                db,
                """
                DELETE FROM notification_events_history
                WHERE tenant_id = :tenant_id
                  AND created_at < :history_cutoff
                """,
                params,
            )
            counters["logs_purged"] += _execute(
                db,
                """
                DELETE FROM notification_logs_history
                WHERE tenant_id = :tenant_id
                  AND created_at < :history_cutoff
                """,
                params,
            )
            counters["jobs_purged"] += _execute(
                db,
                """
                DELETE FROM notification_delivery_jobs_history
                WHERE tenant_id = :tenant_id
                  AND (
                    (status = 'DEAD_LETTERED' AND created_at < :dead_letter_cutoff)
                    OR (status <> 'DEAD_LETTERED' AND created_at < :history_cutoff)
                  )
                """,
                params,
            )

        db.commit()

    return counters


def _is_tenant_deactivated_and_purgeable(ctx: TenantRetentionContext, now: datetime) -> bool:
    status = (ctx.tenant_status or "").upper()
    if status != "DEACTIVATED":
        return False
    cutoff = now - timedelta(days=ctx.purge_after_deactivation_days)
    return _to_utc(ctx.tenant_updated_at) <= cutoff


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _load_tenant_contexts(db: Session) -> list[TenantRetentionContext]:
    rows = db.execute(
        text(
            """
            SELECT
                t.id AS tenant_id,
                t.status AS tenant_status,
                t.updated_at AS tenant_updated_at,
                COALESCE(p.active_retention_days, :active_days) AS active_retention_days,
                COALESCE(p.notification_history_retention_days, :history_days) AS notification_history_retention_days,
                COALESCE(p.dead_letter_retention_days, :dead_letter_days) AS dead_letter_retention_days,
                COALESCE(p.purge_after_deactivation_days, :deactivate_days) AS purge_after_deactivation_days,
                COALESCE(p.archive_enabled, true) AS archive_enabled,
                COALESCE(p.purge_enabled, true) AS purge_enabled
            FROM tenants t
            LEFT JOIN tenant_data_retention_policy p
              ON p.tenant_id = t.id
            ORDER BY t.created_at ASC
            """
        ),
        {
            "active_days": settings.notification_retention_active_days_default,
            "history_days": settings.notification_retention_history_days_default,
            "dead_letter_days": settings.notification_retention_dead_letter_days_default,
            "deactivate_days": settings.notification_purge_after_deactivation_days_default,
        },
    ).mappings().all()

    contexts: list[TenantRetentionContext] = []
    for row in rows:
        contexts.append(
            TenantRetentionContext(
                tenant_id=str(row["tenant_id"]),
                tenant_status=str(row["tenant_status"] or "ACTIVE"),
                tenant_updated_at=row["tenant_updated_at"],
                active_retention_days=int(row["active_retention_days"]),
                notification_history_retention_days=int(row["notification_history_retention_days"]),
                dead_letter_retention_days=int(row["dead_letter_retention_days"]),
                purge_after_deactivation_days=int(row["purge_after_deactivation_days"]),
                archive_enabled=bool(row["archive_enabled"]),
                purge_enabled=bool(row["purge_enabled"]),
            )
        )
    return contexts


def _execute(db: Session, sql: str, params: dict[str, Any]) -> int:
    result = db.execute(text(sql), params)
    return int(result.rowcount or 0)


def _new_counter() -> dict[str, int]:
    return {
        "events_archived": 0,
        "jobs_archived": 0,
        "logs_archived": 0,
        "events_deleted": 0,
        "jobs_deleted": 0,
        "logs_deleted": 0,
        "events_purged": 0,
        "jobs_purged": 0,
        "logs_purged": 0,
    }
