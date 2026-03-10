from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets


def generate_approval_token() -> str:
    # 32 bytes of entropy gives a high-entropy URL-safe token.
    return secrets.token_urlsafe(32)


def compute_expiry_iso(ttl_hours: int, now: datetime | None = None) -> str:
    base = now or datetime.now(timezone.utc)
    return (base + timedelta(hours=ttl_hours)).isoformat()


def is_expired_iso(expires_at: str, now: datetime | None = None) -> bool:
    expiry = datetime.fromisoformat(expires_at)
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    now_utc = now or datetime.now(timezone.utc)
    return expiry < now_utc
