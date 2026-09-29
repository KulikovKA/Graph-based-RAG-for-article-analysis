"""Начальные проверки доступности; подробная проверка зависимостей появится позже."""

from collections.abc import Mapping

from fastapi import APIRouter, Response, status

router = APIRouter(tags=["health"])


@router.get("/health/live", include_in_schema=True)
async def liveness() -> dict[str, str]:
    return {"status": "live"}


@router.get("/health/ready", include_in_schema=True)
async def readiness(response: Response) -> Mapping[str, str]:
    # Постоянные хранилища пока не подключены; готовность зависимостей не подтверждена.
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "not_ready", "reason": "dependencies_not_configured"}
