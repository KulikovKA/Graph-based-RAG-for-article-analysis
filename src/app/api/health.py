"""Начальные проверки доступности; подробная проверка зависимостей появится позже."""

from collections.abc import Mapping

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import auth_service
from app.storage.models import AnalysisJob

router = APIRouter(tags=["health"])


@router.get("/health/live", include_in_schema=True)
async def liveness() -> dict[str, str]:
    return {"status": "live"}


@router.get("/health/ready", include_in_schema=True)
def readiness(request: Request, response: Response) -> Mapping[str, str]:
    try:
        service = auth_service(request)
        with service.sessions() as db:
            db.scalar(select(AnalysisJob.run_id).limit(1))
        return {"status": "ready"}
    except (HTTPException, SQLAlchemyError):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "reason": "dependencies_not_configured"}
