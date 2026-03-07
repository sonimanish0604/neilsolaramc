from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.db.session import ADMIN_ENGINE

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/ready")
def ready():
    try:
        with ADMIN_ENGINE.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"DB not ready: {exc}")
