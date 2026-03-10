from __future__ import annotations

from datetime import datetime, timezone

from app.notification_engine.maintenance import (
    TenantRetentionContext,
    _is_tenant_deactivated_and_purgeable,
    _to_utc,
)


def _ctx(status: str, updated_at: datetime, purge_after_days: int = 90) -> TenantRetentionContext:
    return TenantRetentionContext(
        tenant_id="00000000-0000-0000-0000-000000000001",
        tenant_status=status,
        tenant_updated_at=updated_at,
        active_retention_days=7,
        notification_history_retention_days=365,
        dead_letter_retention_days=365,
        purge_after_deactivation_days=purge_after_days,
        archive_enabled=True,
        purge_enabled=True,
    )


def test_to_utc_handles_naive_datetime():
    naive = datetime(2026, 3, 10, 10, 0, 0)
    utc = _to_utc(naive)
    assert utc.tzinfo is not None
    assert utc.utcoffset().total_seconds() == 0


def test_deactivated_tenant_purge_window_elapsed():
    now = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
    updated = datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert _is_tenant_deactivated_and_purgeable(_ctx("DEACTIVATED", updated), now)


def test_active_tenant_not_purgeable():
    now = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
    updated = datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert not _is_tenant_deactivated_and_purgeable(_ctx("ACTIVE", updated), now)


def test_deactivated_but_recent_not_purgeable():
    now = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
    updated = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert not _is_tenant_deactivated_and_purgeable(_ctx("DEACTIVATED", updated, purge_after_days=30), now)
