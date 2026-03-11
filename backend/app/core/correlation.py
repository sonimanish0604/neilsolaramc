from __future__ import annotations

import uuid
from contextvars import ContextVar

from fastapi import Request


_CORRELATION_ID: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def generate_correlation_id() -> str:
    return str(uuid.uuid4())


def set_correlation_id(value: str) -> None:
    _CORRELATION_ID.set(value)


def get_correlation_id() -> str | None:
    return _CORRELATION_ID.get()


def get_request_correlation_id(request: Request) -> str:
    existing = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID")
    cid = (existing or "").strip() or generate_correlation_id()
    set_correlation_id(cid)
    return cid
