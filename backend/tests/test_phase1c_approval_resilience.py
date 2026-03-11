from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.schemas.application import SiteCreate
from app.schemas.workorders import ApprovalResendIn
from app.services.approval_tokens import (
    classify_provider_failure,
    compute_next_retry,
    now_utc,
    should_send_reminder,
)


def test_site_create_requires_supervisor_contact():
    with pytest.raises(ValidationError):
        SiteCreate(
            customer_id="c-1",
            site_name="Site A",
            address="addr",
            status="ACTIVE",
        )


def test_site_create_accepts_email_only():
    site = SiteCreate(
        customer_id="c-1",
        site_name="Site A",
        status="ACTIVE",
        site_supervisor_email="supervisor@example.com",
    )
    assert site.site_supervisor_email == "supervisor@example.com"


def test_approval_resend_mode_validation():
    model = ApprovalResendIn(mode="EXTEND")
    assert model.mode == "EXTEND"

    with pytest.raises(ValidationError):
        ApprovalResendIn(mode="INVALID")


def test_should_send_reminder_when_expiry_within_lead_window():
    now_val = now_utc()
    expires_at = (now_val + timedelta(hours=2)).isoformat()

    assert should_send_reminder(
        expires_at=expires_at,
        reminder_count=0,
        status="SENT",
        max_reminders=2,
        lead_hours=24,
        now_dt=now_val,
    )


def test_should_not_send_reminder_when_limit_reached_or_wrong_status():
    now_val = now_utc()
    expires_at = (now_val + timedelta(hours=2)).isoformat()

    assert not should_send_reminder(
        expires_at=expires_at,
        reminder_count=2,
        status="SENT",
        max_reminders=2,
        lead_hours=24,
        now_dt=now_val,
    )
    assert not should_send_reminder(
        expires_at=expires_at,
        reminder_count=0,
        status="SIGNED",
        max_reminders=2,
        lead_hours=24,
        now_dt=now_val,
    )


def test_compute_next_retry_moves_forward():
    first = compute_next_retry(1)
    second = compute_next_retry(2)
    assert second > first


def test_provider_failure_classification_permanent_cases():
    assert not classify_provider_failure("EMAIL", "authentication failed")
    assert not classify_provider_failure("WHATSAPP", "invalid recipient")


def test_provider_failure_classification_retryable_cases():
    assert classify_provider_failure("EMAIL", "timeout while sending")
    assert classify_provider_failure("WHATSAPP", "500 server error")
