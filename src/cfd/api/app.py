"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from cfd import __version__
from cfd.api.middleware import I18nMiddleware
from cfd.api.rate_limit import limiter
from cfd.config.settings import Settings
from cfd.exceptions import (
    AuthorizationError,
    AuthorNotFoundError,
    CFDError,
    DatabaseUnavailableError,
    RateLimitError,
    ValidationError,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown."""
    settings: Settings = app.state.settings

    # Try to connect to Supabase
    if settings.supabase_url and settings.supabase_key:
        try:
            from cfd.db.client import get_supabase_client

            app.state.supabase = get_supabase_client(settings)
            logger.info("Supabase client initialized")
        except Exception:
            logger.warning("Failed to initialize Supabase client", exc_info=True)
            app.state.supabase = None
    else:
        app.state.supabase = None

    yield

    # Cleanup
    app.state.supabase = None


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    s = settings or Settings()

    app = FastAPI(
        title="Citation Fraud Detector API",
        description="REST API for detecting anomalous citation patterns in scientometric databases.",
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.state.settings = s
    app.state.limiter = limiter

    # CORS
    origins = [o.strip() for o in s.api_cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # I18n middleware
    app.add_middleware(I18nMiddleware)

    # Rate limiter
    app.state.limiter = limiter

    # Exception handlers
    @app.exception_handler(AuthorNotFoundError)
    async def _author_not_found(_request: Request, exc: AuthorNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def _validation_error(_request: Request, exc: ValidationError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(AuthorizationError)
    async def _authorization_error(_request: Request, exc: AuthorizationError):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(RateLimitError)
    async def _rate_limit_error(_request: Request, exc: RateLimitError):
        return JSONResponse(status_code=429, content={"detail": str(exc)})

    @app.exception_handler(DatabaseUnavailableError)
    async def _db_unavailable(_request: Request, exc: DatabaseUnavailableError):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(RateLimitExceeded)
    async def _slowapi_rate_limit(_request: Request, exc: RateLimitExceeded):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

    @app.exception_handler(CFDError)
    async def _cfd_error(_request: Request, exc: CFDError):
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    # Register routers
    from cfd.api.routers.health import router as health_router

    app.include_router(health_router)

    # Lazy import remaining routers to avoid import errors when FastAPI deps not installed
    from cfd.api.routers.audit import router as audit_router
    from cfd.api.routers.authors import router as authors_router
    from cfd.api.routers.batch import router as batch_router
    from cfd.api.routers.cris import router as cris_router
    from cfd.api.routers.version import router as version_router
    from cfd.api.routers.watchlist import router as watchlist_router

    app.include_router(authors_router, prefix="/api/v1")
    app.include_router(batch_router, prefix="/api/v1")
    app.include_router(watchlist_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(version_router, prefix="/api/v1")
    app.include_router(cris_router, prefix="/api/v1")

    return app


def run():
    """Entry point for `cfd-api` console script."""
    import uvicorn

    settings = Settings()
    uvicorn.run(
        "cfd.api.app:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
    )
