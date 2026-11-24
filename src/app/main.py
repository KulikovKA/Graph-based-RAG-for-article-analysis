"""Фабрика приложения FastAPI без побочных эффектов при запуске."""

import hashlib
import os
from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware

from app.api.auth import AuthSettings
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.middleware import RequestContextMiddleware
from app.api.routes.conversations import router as conversations_router
from app.api.routes.explorer import router as explorer_router
from app.api.routes.graph import router as graph_router
from app.api.routes.runs import router as runs_router
from app.api.routes.sources import router as sources_router
from app.domain.explorer import ExplorerPort
from app.integrations.redis_cache import RedisCache, RedisClient
from app.services.auth import AuthService
from app.services.memory_cache import ScopedStageCache


def _stage_cache() -> ScopedStageCache | None:
    url = os.getenv("REDIS_URL")
    secret = os.getenv("AUTH_SESSION_SECRET")
    if not url or not secret:
        return None
    scope_secret = hashlib.sha256(b"article-stage-cache-v1\x00" + secret.encode()).digest()
    client = Redis.from_url(url, socket_connect_timeout=0.25, socket_timeout=0.25)
    return ScopedStageCache(RedisCache(cast(RedisClient, client), scope_secret=scope_secret))


def create_app(
    *,
    auth: AuthService | None = None,
    auth_settings: AuthSettings | None = None,
    explorer: ExplorerPort | None = None,
    stage_cache: ScopedStageCache | None = None,
) -> FastAPI:
    application = FastAPI(title="Article Analysis API", version="0.1.0")
    application.state.auth_service = auth
    application.state.auth_settings = auth_settings or AuthSettings.from_env()
    application.state.explorer_port = explorer
    application.state.stage_cache = stage_cache if stage_cache is not None else _stage_cache()

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(application.state.auth_settings.origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key", "Last-Event-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )
    application.add_middleware(RequestContextMiddleware)

    @application.exception_handler(HTTPException)
    async def error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={
                "error": {
                    "code": str(exc.detail),
                    "message": str(exc.detail),
                    "request_id": request.state.request_id,
                }
            },
        )

    @application.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, exc: RequestValidationError) -> JSONResponse:
        return await error(request, HTTPException(422, "INVALID_INPUT"))

    @application.exception_handler(SQLAlchemyError)
    async def database_unavailable(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        return await error(request, HTTPException(503, "QUEUE_UNAVAILABLE"))

    application.include_router(auth_router)
    application.include_router(conversations_router)
    application.include_router(runs_router)
    application.include_router(graph_router)
    application.include_router(explorer_router)
    application.include_router(sources_router)
    application.include_router(health_router)
    return application


app = create_app()
