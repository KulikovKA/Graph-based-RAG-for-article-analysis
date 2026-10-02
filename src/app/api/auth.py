"""Auth API и зависимости для будущих защищённых маршрутов."""

import os
import secrets
from dataclasses import dataclass
from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from app.services.auth import SESSION_SECONDS, AuthService, Principal, csrf_token, normalize_email
from app.storage.models import Conversation
from app.storage.repositories import OwnedRepository, make_engine, make_session_factory

COOKIE_NAME = "article_session"
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@dataclass(frozen=True)
class AuthSettings:
    origins: tuple[str, ...] = ()
    http_dev_enabled: bool = False
    cookie_secure: bool = True
    login_ip_limit: int = 20
    login_account_limit: int = 10
    request_ip_limit: int = 300
    request_user_limit: int = 120

    def __post_init__(self) -> None:
        if not self.cookie_secure and not self.http_dev_enabled:
            raise ValueError("Небезопасная cookie требует явного HTTP dev opt-in")
        for origin in self.origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or (parsed.scheme == "http" and not self.http_dev_enabled)
            ):
                raise ValueError("Origin должен содержать только разрешённые scheme/host/port")

    @classmethod
    def from_env(cls) -> "AuthSettings":
        dev = (
            os.getenv("APP_ENV", "development") == "development"
            and os.getenv("APP_HTTP_DEV_ENABLED", "false").lower() == "true"
        )
        return cls(
            origins=tuple(
                x.strip() for x in os.getenv("AUTH_ALLOWED_ORIGINS", "").split(",") if x.strip()
            ),
            http_dev_enabled=dev,
            cookie_secure=os.getenv("AUTH_COOKIE_SECURE", "true").lower() != "false",
        )


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024, repr=False)


class SessionBody(BaseModel):
    user_id: UUID
    csrf_token: str


def auth_service(request: Request) -> AuthService:
    service: AuthService | None = request.app.state.auth_service
    if service is None:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise HTTPException(503, "AUTH_UNAVAILABLE")
        service = AuthService(make_session_factory(make_engine(url)))
        request.app.state.auth_service = service
    return service


def settings(request: Request) -> AuthSettings:
    config: AuthSettings = request.app.state.auth_settings
    return config


def transport(request: Request) -> None:
    if request.url.scheme != "https" and not settings(request).http_dev_enabled:
        raise HTTPException(403, "HTTPS_REQUIRED")


def origin(request: Request) -> None:
    transport(request)
    if request.headers.get("origin") not in settings(request).origins:
        raise HTTPException(403, "INVALID_ORIGIN")


def enforce_limit(service: AuthService, key: str, limit: int) -> None:
    retry = service.rate_limit(key, limit)
    if retry is not None:
        raise HTTPException(429, "RATE_LIMITED", headers={"Retry-After": str(retry)})


def ip_key(request: Request) -> str:
    # Только ASGI client: доверие forwarded headers настраивается в сервере, не по вводу клиента.
    return request.client.host if request.client else "unknown"


def require_owner(
    request: Request, service: Annotated[AuthService, Depends(auth_service)]
) -> Principal:
    transport(request)
    config = settings(request)
    enforce_limit(service, "request-ip:" + ip_key(request), config.request_ip_limit)
    principal = service.authenticate(request.cookies.get(COOKIE_NAME))
    if principal is None:
        raise HTTPException(401, "UNAUTHENTICATED")
    enforce_limit(service, "request-user:" + str(principal.user_id), config.request_user_limit)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin(request)
        supplied = request.headers.get("x-csrf-token", "")
        if not secrets.compare_digest(supplied.encode("utf-8"), principal.csrf.encode("utf-8")):
            raise HTTPException(403, "INVALID_CSRF")
    return principal


def owned_conversation(db: Session, principal: Principal, conversation_id: UUID) -> Conversation:
    conversation = OwnedRepository(db).conversation(principal.user_id, conversation_id)
    if conversation is None:
        raise HTTPException(404, "NOT_FOUND")
    return conversation


async def login_body(request: Request) -> LoginBody:
    origin(request)
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 8192:
            raise HTTPException(413, "REQUEST_TOO_LARGE")
    try:
        body = LoginBody.model_validate_json(data)
        normalize_email(body.email)
        return body
    except (ValidationError, ValueError):
        raise HTTPException(422, "INVALID_INPUT") from None


@router.post(
    "/login",
    response_model=SessionBody,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": LoginBody.model_json_schema()}},
        }
    },
)
def login(
    request: Request,
    response: Response,
    body: Annotated[LoginBody, Depends(login_body)],
    service: Annotated[AuthService, Depends(auth_service)],
) -> SessionBody:
    config = settings(request)
    enforce_limit(service, "login-ip:" + ip_key(request), config.login_ip_limit)
    enforce_limit(
        service, "login-account:" + normalize_email(body.email), config.login_account_limit
    )
    result = service.login(body.email, body.password, request.cookies.get(COOKIE_NAME))
    if result is None:
        raise HTTPException(401, "INVALID_CREDENTIALS")
    user_id, token = result
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=config.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return SessionBody(user_id=user_id, csrf_token=csrf_token(token))


@router.get("/session", response_model=SessionBody)
def session(
    response: Response, principal: Annotated[Principal, Depends(require_owner)]
) -> SessionBody:
    response.headers["Cache-Control"] = "no-store"
    return SessionBody(user_id=principal.user_id, csrf_token=principal.csrf)


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    principal: Annotated[Principal, Depends(require_owner)],
    service: Annotated[AuthService, Depends(auth_service)],
) -> Response:
    service.logout(principal)
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(
        COOKIE_NAME, secure=settings(request).cookie_secure, httponly=True, samesite="lax", path="/"
    )
    return response
