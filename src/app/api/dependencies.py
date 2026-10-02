"""Короткие транзакции, безопасные ошибки и bounded JSON body."""

import json
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth import auth_service
from app.services.auth import AuthService


def database(service: Annotated[AuthService, Depends(auth_service)]) -> Iterator[Session]:
    try:
        with service.sessions.begin() as db:
            yield db
    except SQLAlchemyError:
        raise HTTPException(503, "QUEUE_UNAVAILABLE") from None


async def bounded_json(request: Request) -> dict[str, Any]:
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > 16384:
            raise HTTPException(413, "REQUEST_TOO_LARGE")
        data.extend(chunk)
    try:
        value = json.loads(data)
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (ValueError, UnicodeError):
        raise HTTPException(422, "INVALID_INPUT") from None
