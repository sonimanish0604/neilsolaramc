from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from app.services.approval_tokens import now_utc, parse_iso
from app.services.report_jobs import build_idempotency_key, compute_report_retry_at


def test_report_idempotency_key_contains_workorder_and_mode():
    workorder_id = uuid4()
    key = build_idempotency_key(workorder_id=workorder_id, is_final=True)
    assert str(workorder_id) in key
    assert ":final:" in key


def test_report_retry_time_is_in_future():
    retry_at = compute_report_retry_at(1)
    assert parse_iso(retry_at) > now_utc() - timedelta(seconds=1)


def test_report_retry_backoff_increases():
    first = parse_iso(compute_report_retry_at(1))
    second = parse_iso(compute_report_retry_at(2))
    assert second > first
