"""Фабрика приложения FastAPI без побочных эффектов при запуске."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.api.auth import AuthSettings
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.middleware import RequestContextMiddleware
from app.api.routes.conversations import router as conversations_router
from app.api.routes.graph import router as graph_router
from app.api.routes.runs import router as runs_router
from app.api.routes.sources import router as sources_router
from app.services.auth import AuthService


def create_app(
    *, auth: AuthService | None = None, auth_settings: AuthSettings | None = None
) -> FastAPI:
    application = FastAPI(title="Article Analysis API", version="0.1.0")
    application.state.auth_service = auth
    application.state.auth_settings = auth_settings or AuthSettings.from_env()

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
    application.include_router(sources_router)
    application.include_router(health_router)
    return application


app = create_app()
