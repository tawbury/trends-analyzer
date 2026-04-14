from __future__ import annotations

from fastapi import FastAPI

from src.api.routes.analyze import router as analyze_router
from src.shared.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Trend Intelligence Platform MVP")
    app.include_router(analyze_router)
    return app


app = create_app()
