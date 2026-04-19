from __future__ import annotations

from fastapi import FastAPI

from src.api.errors import ApiError, api_error_handler
from src.api.routes.analyze import router as analyze_router
from src.api.routes.generic import router as generic_router
from src.api.routes.ingest import router as ingest_router
from src.api.routes.notifications import router as notifications_router
from src.api.routes.ops import router as ops_router
from src.api.routes.qts import router as qts_router
from src.api.routes.signals import router as signals_router
from src.api.routes.workflow import router as workflow_router
from src.shared.logging import configure_logging
from src.shared.middlewares import DeviceIDMiddleware, MarketHoursMiddleware


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Trend Intelligence Platform MVP")
    app.add_exception_handler(ApiError, api_error_handler)
    
    # Register Middlewares
    app.add_middleware(DeviceIDMiddleware)
    app.add_middleware(MarketHoursMiddleware)
    
    app.include_router(analyze_router, prefix="/api/v1")
    app.include_router(ingest_router, prefix="/api/v1")
    app.include_router(signals_router, prefix="/api/v1")
    app.include_router(qts_router, prefix="/api/v1")
    app.include_router(generic_router, prefix="/api/v1")
    app.include_router(workflow_router, prefix="/api/v1")
    app.include_router(notifications_router, prefix="/api/v1")
    app.include_router(ops_router, prefix="/api/v1")
    return app


app = create_app()
