"""Публичные проекции snapshot без приватных drafts и произвольных URL."""

from typing import Any
from urllib.parse import urlsplit

from fastapi import HTTPException
from pydantic import ValidationError

from app.domain.contracts import RunV1
from app.services.run_events import run_snapshot
from app.storage.models import AnalysisRun

SOURCE_HOSTS = {"worldwide.espacenet.com", "openalex.org", "doi.org", "patents.google.com"}


def source_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in SOURCE_HOSTS
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
    ):
        raise HTTPException(503, "INVALID_SOURCE_METADATA")
    return value


def public_run(run: AnalysisRun) -> RunV1:
    return public_snapshot(run_snapshot(run))


def public_snapshot(value: dict[str, Any]) -> RunV1:
    data = dict(value)
    if not data.get("coverage"):
        data["coverage"] = {
            "sources": [],
            "channels": [],
            "partial": False,
            "historical": bool(data.get("source_run_id")),
        }
    if data.get("status") != "completed":
        for field in ("answer", "public_analysis", "answer_presentation", "outcome"):
            data[field] = None
    data["graph_url"] = None
    try:
        dto = RunV1.model_validate(data)
        for source in dto.sources:
            source_url(source.url)
        return dto
    except (ValidationError, ValueError):
        raise HTTPException(503, "INVALID_STORED_RESULT") from None
