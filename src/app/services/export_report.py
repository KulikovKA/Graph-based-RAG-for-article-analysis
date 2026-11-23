"""Экспорт сохранённого исследования без обращения к поиску и моделям."""

import json
from html import escape
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.projections import public_run, source_url
from app.domain.contracts import ClaimV1
from app.domain.planner import IdeaV1
from app.storage.models import AnalysisRun, EvidenceChunk, IdeaVersion, RunEvidence


def render_export(db: Session, run: AnalysisRun) -> str:
    dto = public_run(run)
    if dto.answer is None or dto.outcome is None:
        raise ValueError("INVALID_STORED_RESULT")
    version = None
    labels: dict[UUID, str] = {}
    if run.idea_version_id:
        version = db.scalar(
            select(IdeaVersion).where(
                IdeaVersion.id == run.idea_version_id,
                IdeaVersion.conversation_id == run.conversation_id,
            )
        )
        if version is None:
            raise ValueError("INVALID_IDEA_SNAPSHOT")
        idea = IdeaV1.model_validate_json(json.dumps(version.normalized_json))
        labels = {feature.id: feature.text for feature in idea.features}

    rows = db.execute(
        select(RunEvidence, EvidenceChunk)
        .join(EvidenceChunk, EvidenceChunk.id == RunEvidence.chunk_id)
        .where(RunEvidence.run_id == run.id)
    ).all()
    evidence: dict[UUID, RunEvidence] = {}
    chunks: dict[UUID, EvidenceChunk] = {}
    for item, chunk in rows:
        if (
            item.run_id != run.id
            or item.evidence_id in evidence
            or item.revision_id != chunk.revision_id
            or item.span_start < 0
            or item.span_end <= item.span_start
            or item.span_end > len(chunk.text)
            or chunk.text[item.span_start : item.span_end] != item.quoted_span
        ):
            raise ValueError("INVALID_EVIDENCE_SNAPSHOT")
        source_url(item.source_url)
        evidence[item.evidence_id] = item
        chunks[item.evidence_id] = chunk

    snapshot = run.evidence_snapshot_json or {}
    if not isinstance(snapshot, dict):
        raise ValueError("INVALID_EVIDENCE_SNAPSHOT")
    if "evidence" in snapshot:
        raw = snapshot["evidence"]
        if not isinstance(raw, list) or len(raw) != len(evidence):
            raise ValueError("INVALID_EVIDENCE_SNAPSHOT")
        seen: set[UUID] = set()
        for entry in raw:
            eid = UUID(str(entry["evidence_id"]))
            item = evidence.get(eid)
            if item is None or eid in seen:
                raise ValueError("INVALID_EVIDENCE_SNAPSHOT")
            seen.add(eid)
            for key in ("document_id", "revision_id", "chunk_id"):
                if UUID(str(entry[key])) != getattr(item, key):
                    raise ValueError("INVALID_EVIDENCE_SNAPSHOT")
            for key in ("span_start", "span_end", "quoted_span"):
                if entry[key] != getattr(item, key):
                    raise ValueError("INVALID_EVIDENCE_SNAPSHOT")
            if entry["section"] != chunks[eid].section or entry["language"] != chunks[eid].language:
                raise ValueError("INVALID_EVIDENCE_SNAPSHOT")
            if entry["canonical_url"] != item.source_url:
                raise ValueError("INVALID_EVIDENCE_SNAPSHOT")

    source_ids: set[UUID] = set()
    for source in dto.sources:
        for eid in source.evidence_ids:
            item = evidence.get(eid)
            if (
                item is None
                or eid in source_ids
                or item.document_id != source.document_id
                or item.revision_id != source.revision_id
                or item.source_url != source.url
            ):
                raise ValueError("INVALID_SOURCE_METADATA")
            source_ids.add(eid)
    if source_ids != set(evidence):
        raise ValueError("INVALID_SOURCE_METADATA")

    def check(claim: ClaimV1, document_id: UUID | None = None) -> None:
        for eid in claim.evidence_ids:
            item = evidence.get(eid)
            if item is None or (document_id is not None and item.document_id != document_id):
                raise ValueError("INVALID_CITATION")
        for quote in claim.quotes:
            item = evidence.get(quote.evidence_id)
            if (
                item is None
                or quote.evidence_id not in claim.evidence_ids
                or quote.start < item.span_start
                or quote.end > item.span_end
                or item.quoted_span[quote.start - item.span_start : quote.end - item.span_start]
                != quote.text
            ):
                raise ValueError("INVALID_QUOTE")

    for claim in dto.answer.summary:
        check(claim)
    for match in dto.answer.matches:
        if version is not None and match.feature_id not in labels:
            raise ValueError("INVALID_FEATURE")
        for claim in match.claims:
            check(claim, match.document_id)
    for difference in dto.answer.differences:
        if version is not None and difference.feature_id not in labels:
            raise ValueError("INVALID_FEATURE")
        for claim in difference.claims:
            check(claim)
    if dto.outcome in {"no_evidence", "clarification"} and (
        dto.answer.summary or dto.answer.matches or dto.answer.differences
    ):
        raise ValueError("INVALID_EMPTY_RESULT")

    def esc(value: Any) -> str:
        return escape(str(value), quote=True)

    def claims(items: list[ClaimV1]) -> str:
        return "".join(
            "<li>"
            + esc(c.text)
            + " "
            + esc(", ".join(map(str, c.evidence_ids)))
            + "<ul>"
            + "".join(
                "<li>"
                + esc(q.text)
                + " ("
                + esc(q.evidence_id)
                + ", "
                + esc(q.start)
                + "–"
                + esc(q.end)
                + ")</li>"
                for q in c.quotes
            )
            + "</ul></li>"
            for c in items
        )

    parts = [
        '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        "<title>Отчёт исследования</title></head><body><h1>Отчёт исследования</h1>",
        "<p>Run: "
        + esc(run.id)
        + "; результат: "
        + esc(dto.outcome)
        + "; версия идеи: "
        + esc(run.idea_version_id or "нет")
        + "; номер версии: "
        + esc(version.version_no if version else "нет")
        + "; исходный run: "
        + esc(run.source_run_id or "нет")
        + "; поколение индекса: "
        + esc(run.index_generation_id or "нет")
        + "</p>",
        "<h2>Выводы</h2><ul>" + claims(dto.answer.summary) + "</ul>",
        "<h2>Сравнение признаков</h2><ul>",
    ]
    for match in dto.answer.matches:
        parts.append(
            "<li>"
            + esc(labels.get(match.feature_id, str(match.feature_id)))
            + " — документ "
            + esc(match.document_id)
            + "<ul>"
            + claims(match.claims)
            + "</ul></li>"
        )
    for difference in dto.answer.differences:
        parts.append(
            "<li>"
            + esc(labels.get(difference.feature_id, str(difference.feature_id)))
            + "<ul>"
            + claims(difference.claims)
            + "</ul></li>"
        )
    parts.append(
        "</ul><h2>Патенты и публикации</h2><table><thead><tr><th>Название</th>"
        "<th>Тип</th><th>Документ</th><th>Ревизия</th><th>Дата</th></tr></thead><tbody>"
    )
    for source in dto.sources:
        parts.append(
            '<tr><td><a href="'
            + esc(source.url)
            + '">'
            + esc(source.title)
            + "</a></td><td>"
            + esc(source.kind)
            + "</td><td>"
            + esc(source.document_id)
            + "</td><td>"
            + esc(source.revision_id)
            + "</td><td>"
            + esc(source.publication_date or "")
            + "</td></tr>"
        )
    parts.append("</tbody></table><h2>Источники и evidence</h2><ul>")
    for item in sorted(evidence.values(), key=lambda row: str(row.evidence_id)):
        parts.append(
            "<li>"
            + esc(item.evidence_id)
            + ": "
            + esc(item.quoted_span)
            + " (фрагмент "
            + esc(item.chunk_id)
            + ", "
            + esc(item.span_start)
            + "–"
            + esc(item.span_end)
            + ")</li>"
        )
    parts.append(
        "</ul><h2>Покрытие</h2><pre>"
        + esc(dto.coverage.model_dump_json())
        + "</pre><h2>Ограничения</h2><ul>"
        + "".join(
            "<li>" + esc(x.code) + ": " + esc(x.message) + "</li>" for x in dto.answer.limitations
        )
        + "</ul><h2>Следующие вопросы</h2><ul>"
        + "".join("<li>" + esc(x) + "</li>" for x in dto.answer.followup_suggestions)
        + "</ul><p>Предварительное техническое исследование.</p></body></html>"
    )
    return "".join(parts)
