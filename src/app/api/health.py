"""Bootstrap liveness/readiness endpoints; detailed capability health is added with infra."""

from collections.abc import Mapping

from fastapi import APIRouter, Response, status

router = APIRouter(tags=["health"])


@router.get("/health/live", include_in_schema=True)
async def liveness() -> dict[str, str]:
    return {"status": "live"}


@router.get("/health/ready", include_in_schema=True)
async def readiness(response: Response) -> Mapping[str, str]:
    # Bootstrap has no durable stores yet. Do not imply dependency readiness.
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "not_ready", "reason": "dependencies_not_configured"}
