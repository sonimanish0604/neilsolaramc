from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.notification import NotificationEvent


def publish_notification_event(
    db: Session,
    tenant_id: UUID,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict[str, Any],
) -> NotificationEvent:
    event = NotificationEvent(
        tenant_id=tenant_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_json=payload,
        status="PENDING",
    )
    db.add(event)
    db.flush()
    return event
