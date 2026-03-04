from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.routes.health import router as health_router
from app.api.routes.workorders import router as workorders_router
from app.api.routes.approvals import router as approvals_router
from app.api.routes.logos import router as logos_router

setup_logging()

app = FastAPI(title=settings.app_name)

app.include_router(health_router)
app.include_router(workorders_router)
app.include_router(approvals_router)
app.include_router(logos_router)