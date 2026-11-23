"""Ограниченный мост к существующим EPO/OpenAlex адаптерам.

Методы асинхронны; вызывающий интеграционный порт отвечает за event loop и лимит
запросов. Этот модуль не хранит страницы и не публикует индекс.
"""

import hashlib
import json
import re
from dataclasses import asdict, dataclass

from app.domain.documents import NormalizedDocument
from app.domain.source import SourceStatus
from app.integrations.epo import EpoOpsClient
from app.integrations.openalex import OpenAlexClient
from app.services.ingestion import canonical_external_id
from app.workers.ingest import from_epo, from_openalex

from .pipeline import Interval, Item, Page, PipelineError, RetryableError, Source


@dataclass(frozen=True)
class SourceScope:
    """Только доверенная операторская конфигурация, не значения dag_run.conf."""

    query: str
    filters: str | None = None

    def validate(self) -> None:
        if (
            not self.query.strip()
            or len(self.query) > 2000
            or (self.filters is not None and (not self.filters.strip() or len(self.filters) > 2000))
        ):
            raise PipelineError("invalid_scope")


def _revision(document: NormalizedDocument) -> str:
    payload = asdict(document)
    payload["external_id"] = canonical_external_id(document.source, document.external_id)
    value = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _status(status: SourceStatus, error_code: str | None) -> None:
    if status in (SourceStatus.OK, SourceStatus.EMPTY):
        return
    if error_code in {"rate_limited", "quota_exhausted", "network_error", "server_error"}:
        raise RetryableError("source_unavailable")
    raise PipelineError("source_unavailable")


def _epo_id(value: str) -> str:
    canonical = canonical_external_id("epo_ops", value)
    match = re.fullmatch(r"([A-Z]{2})([A-Z0-9]+)([A-Z][0-9]?)", canonical)
    if match is None:
        raise PipelineError("invalid_document")
    return ".".join(match.groups())


class SourceBridge:
    def __init__(
        self,
        *,
        epo: EpoOpsClient,
        openalex: OpenAlexClient,
        epo_scope: SourceScope,
        openalex_scope: SourceScope,
    ) -> None:
        epo_scope.validate()
        openalex_scope.validate()
        self.epo = epo
        self.openalex = openalex
        self.epo_scope = epo_scope
        self.openalex_scope = openalex_scope

    async def discover(
        self, source: Source, interval: Interval, cursor: str | None, limit: int
    ) -> Page:
        interval.validate(366)
        if limit < 1 or limit > 100:
            raise PipelineError("invalid_limits")
        if source == "epo_ops":
            if cursor is not None and (
                not cursor.isascii()
                or not cursor.isdecimal()
                or len(cursor) > 4
                or int(cursor) >= 2000
            ):
                raise PipelineError("invalid_cursor")
            result = await self.epo.search(
                self.epo_scope.query,
                limit=limit,
                offset=int(cursor or "0"),
                filters=self.epo_scope.filters,
            )
            _status(result.status, result.error_code)
            if result.status == SourceStatus.OK and (
                result.total_count is None
                or (result.total_count > 2000 and result.next_offset is None)
            ):
                raise PipelineError("source_limit")
            identifiers = [
                canonical_external_id(source, doc.external_id) for doc in result.documents
            ]
            next_cursor = str(result.next_offset) if result.next_offset is not None else None
        elif source == "openalex":
            result_works = await self.openalex.search(
                self.openalex_scope.query,
                per_page=limit,
                cursor=cursor or "*",
                filters=self.openalex_scope.filters,
            )
            _status(result_works.status, result_works.error_code)
            identifiers = [
                canonical_external_id(source, work.external_id) for work in result_works.works
            ]
            next_cursor = result_works.next_cursor
        else:
            raise PipelineError("unsupported_source")
        items = []
        for identifier in identifiers:
            document = await self._fetch(source, identifier)
            items.append(Item(identifier, _revision(document)))
        return Page(tuple(items), next_cursor)

    async def _fetch(self, source: Source, external_id: str) -> NormalizedDocument:
        canonical = canonical_external_id(source, external_id)
        if source == "epo_ops":
            patents = await self.epo.fetch(_epo_id(canonical))
            _status(patents.status, patents.error_code)
            if len(patents.documents) != 1:
                raise PipelineError("invalid_document")
            document = from_epo(patents.documents[0])
        elif source == "openalex":
            works = await self.openalex.fetch(canonical)
            _status(works.status, works.error_code)
            if len(works.works) != 1:
                raise PipelineError("invalid_document")
            document = from_openalex(works.works[0])
        else:
            raise PipelineError("unsupported_source")
        if canonical_external_id(source, document.external_id) != canonical:
            raise PipelineError("invalid_document")
        return document

    async def fetch_pinned(self, source: Source, item: Item) -> NormalizedDocument:
        document = await self._fetch(source, item.external_id)
        if _revision(document) != item.revision_key:
            raise PipelineError("revision_changed")
        return document
