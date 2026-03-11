from fastapi import FastAPI
from fastapi import Request

from app.core.config import settings
from app.core.correlation import get_request_correlation_id
from app.core.logging import setup_logging
from app.api.routes.health import router as health_router
from app.api.routes.workorders import router as workorders_router
from app.api.routes.approvals import router as approvals_router
from app.api.routes.logos import router as logos_router
from app.api.routes.admin import router as admin_router
from app.api.routes.application import router as application_router

setup_logging()

app = FastAPI(title=settings.app_name)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    correlation_id = get_request_correlation_id(request)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response

app.include_router(health_router)
app.include_router(admin_router)
app.include_router(application_router)
app.include_router(workorders_router)
app.include_router(approvals_router)
app.include_router(logos_router)
