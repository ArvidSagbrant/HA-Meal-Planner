"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .api.routes import ai, meals, plans, system
from .config import Settings
from .container import Container
from .errors import (
    AIUnavailableError,
    ConflictError,
    InvalidOperationError,
    MealPlannerError,
    NotFoundError,
    PlanningError,
)
from .middleware import NormalizeIngressPathMiddleware


LOGGER = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or Settings.from_environment()
    container = Container.build(runtime_settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        logging.basicConfig(
            level=runtime_settings.log_level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        container.database.initialize()
        container.meals.prune_images()
        container.mqtt.start()
        LOGGER.info("Meal Planner %s started", __version__)
        try:
            yield
        finally:
            container.mqtt.stop()
            container.ai.close()
            LOGGER.info("Meal Planner stopped")

    application = FastAPI(
        title="Meal Planner API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    application.state.container = container
    application.add_middleware(NormalizeIngressPathMiddleware)

    @application.middleware("http")
    async def enforce_ingress_source(request: Request, call_next):
        if runtime_settings.ingress_only:
            client_host = request.client.host if request.client else None
            if client_host not in {"172.30.32.2", "127.0.0.1", "::1"}:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Access is only available through Home Assistant Ingress"},
                )
        return await call_next(request)

    application.include_router(system.router, prefix="/api")
    application.include_router(ai.router, prefix="/api")
    application.include_router(meals.router, prefix="/api")
    application.include_router(plans.router, prefix="/api")

    @application.exception_handler(MealPlannerError)
    async def application_error_handler(
        _request: Request, error: MealPlannerError
    ) -> JSONResponse:
        if isinstance(error, NotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(error, (ConflictError, PlanningError)):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(error, InvalidOperationError):
            status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(error, AIUnavailableError):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_400_BAD_REQUEST
        return JSONResponse(
            status_code=status_code,
            content={"detail": str(error), "code": error.__class__.__name__},
        )

    static_directory = Path(__file__).with_name("static")
    application.mount("/", StaticFiles(directory=static_directory, html=True), name="frontend")
    return application


app = create_app()
