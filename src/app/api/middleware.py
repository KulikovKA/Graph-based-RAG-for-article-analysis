"""ASGI request context без дополнительного буфера поверх SSE."""

from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        identifier = str(uuid4())
        scope.setdefault("state", {})["request_id"] = identifier

        async def with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = identifier
                if scope["path"].startswith("/api/v1/"):
                    headers["Cache-Control"] = "no-store"
            await send(message)

        if scope["path"].startswith("/api/v1/"):
            supplied = Headers(scope=scope).getlist("origin")
            allowed = scope["app"].state.auth_settings.origins
            if supplied and (len(supplied) != 1 or supplied[0] not in allowed):
                response = JSONResponse(
                    {
                        "error": {
                            "code": "INVALID_ORIGIN",
                            "message": "INVALID_ORIGIN",
                            "request_id": identifier,
                        }
                    },
                    status_code=403,
                )
                await response(scope, receive, with_headers)
                return
        await self.app(scope, receive, with_headers)
