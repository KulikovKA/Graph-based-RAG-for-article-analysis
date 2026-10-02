"""Фабрика приложения FastAPI без побочных эффектов при запуске."""

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.api.auth import AuthSettings
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.services.auth import AuthService


def create_app(
    *, auth: AuthService | None = None, auth_settings: AuthSettings | None = None
) -> FastAPI:
    application = FastAPI(title="Article Analysis API", version="0.1.0")
    application.state.auth_service = auth
    application.state.auth_settings = auth_settings or AuthSettings.from_env()

    @application.middleware("http")
    async def request_id(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        if request.url.path.startswith("/api/v1/auth/"):
            response.headers["Cache-Control"] = "no-store"
        return response

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

    application.include_router(auth_router)
    application.include_router(health_router)
    return application


app = create_app()
