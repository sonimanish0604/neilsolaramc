from pydantic import BaseModel


class LogoSetIn(BaseModel):
    object_path: str  # e.g., "logos/tenants/<tenant_id>/logo.png"


class LogoOut(BaseModel):
    object_path: str | None = None
    signed_url: str | None = None  # placeholder for Phase 2