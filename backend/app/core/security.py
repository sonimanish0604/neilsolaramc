from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from google.auth.transport import requests as grequests
from google.oauth2 import id_token

from app.core.config import settings


@dataclass(frozen=True)
class AuthContext:
    firebase_uid: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    raw_claims: Dict[str, Any] | None = None


def _get_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    return auth.removeprefix("Bearer ").strip()


def verify_firebase_jwt(request: Request) -> AuthContext:
    """
    Verifies Firebase Auth JWT using Google public certs.
    In local dev you can set AUTH_DISABLED=true to bypass auth.
    """
    if settings.auth_disabled:
        # local-dev fallback
        return AuthContext(firebase_uid="local-dev-user", email="local@dev", raw_claims={"dev": True})

    token = _get_bearer_token(request)
    try:
        req = grequests.Request()
        claims = id_token.verify_firebase_token(token, req)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}")

    firebase_uid = claims.get("user_id") or claims.get("sub")
    if not firebase_uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing user_id/sub")

    return AuthContext(
        firebase_uid=firebase_uid,
        email=claims.get("email"),
        phone_number=claims.get("phone_number"),
        raw_claims=claims,
    )