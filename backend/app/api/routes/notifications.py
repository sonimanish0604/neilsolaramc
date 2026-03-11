from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.config import settings
from app.core.secrets import get_secret
from app.notification_engine.channels.mailgun_adapter import send_mailgun_email_direct
from app.schemas.notifications import TrySendEmailIn, TrySendEmailOut

router = APIRouter(prefix="/notifications", tags=["notifications"])

PRIMARY_MAILGUN_DOMAIN = "mail.nogginhausenergy.org"
SANDBOX_MAILGUN_DOMAIN = "sandbox9bda718abe274fbdba9871938c5b1022.mailgun.org"


def require_admin_key(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    expected = settings.bootstrap_admin_key
    if not expected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin API key not configured")
    if x_admin_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin key")


def _resolve_mailgun_domain(domain_selector: int, explicit_domain: str | None) -> str:
    if explicit_domain and explicit_domain.strip():
        return explicit_domain.strip()
    if domain_selector == 2:
        return SANDBOX_MAILGUN_DOMAIN
    return PRIMARY_MAILGUN_DOMAIN


@router.post("/trysendemail", response_model=TrySendEmailOut, dependencies=[Depends(require_admin_key)])
def try_send_email(payload: TrySendEmailIn):
    if settings.app_env.lower() not in {"local", "dev", "test"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Endpoint is only available in local/dev")

    configured_mailgun_key = get_secret(
        logical_name="NOTIFICATION_MAILGUN_API_KEY",
        inline_value=settings.notification_mailgun_api_key,
        secret_ref=settings.notification_mailgun_api_key_secret,
    )
    domain = _resolve_mailgun_domain(payload.domain_selector, payload.mailgun_domain)
    api_key = (payload.mailgun_api_key or configured_mailgun_key or "").strip()
    sender = (payload.from_email or settings.notification_email_from or "").strip()
    eu_region = payload.mailgun_eu_region
    if eu_region is None:
        eu_region = settings.notification_mailgun_eu_region

    if not api_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mailgun_api_key is required")
    if not sender:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="from_email is required")

    result = send_mailgun_email_direct(
        recipient=payload.to,
        subject=payload.subject,
        body=payload.text,
        domain=domain,
        api_key=api_key,
        sender=sender,
        eu_region=eu_region,
        timeout_seconds=settings.notification_mailgun_timeout_seconds,
    )
    if result.status != "SENT":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.error_message or "Mailgun send failed",
        )

    return TrySendEmailOut(
        status=result.status,
        provider=result.provider,
        provider_message_id=result.provider_message_id,
        detail=result.error_message,
        used_domain_selector=payload.domain_selector,
        used_domain=domain,
        used_from=sender,
    )
