"""Публичная metadata источника без run-scoped данных."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.projections import source_url
from app.api.routes.conversations import DB, Owner
from app.storage.models import SourceDocument

router = APIRouter(prefix="/api/v1/sources", tags=["sources"])


@router.get("/{document_id}")
def source(document_id: UUID, owner: Owner, db: DB) -> dict[str, object]:
    row = db.get(SourceDocument, document_id)
    if row is None:
        raise HTTPException(404, "NOT_FOUND")
    return {
        "document_id": row.id,
        "title": row.title,
        "kind": row.kind,
        "publication_date": row.publication_date,
        "url": source_url(row.canonical_url),
    }
