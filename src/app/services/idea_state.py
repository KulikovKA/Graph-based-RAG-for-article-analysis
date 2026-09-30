"""Однократное применение planner под lease/CAS и выбор сохранённого evidence.

Сервис не фиксирует транзакцию: вызывающий worker использует session.begin().
Вызов LLM выполняется до apply; внутри транзакции контекст проверяется повторно.
"""

import copy
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.planner import (
    PROMPT_VERSION,
    ClosedModel,
    EvidenceSource,
    IdeaV1,
    Intent,
    PlannerContext,
    PlannerV1,
    RetrievalKey,
    apply_patch,
    clarify,
    normalize_plan,
    requires_retrieval,
    state_hash,
)
from app.storage.jobs import JobRepository
from app.storage.models import AnalysisRun, Conversation, Idea, IdeaVersion, RunEvidence, utcnow
from app.storage.repositories import OwnedRepository, VersionConflict


class PlannerFenceLost(Exception):
    """Worker утратил аренду или запуск отменён; изменения не разрешены."""


class PlannerDecision(ClosedModel):
    prompt_version: str = PROMPT_VERSION
    intent: Intent
    requires_retrieval: bool
    historical: bool
    source_run_id: UUID | None
    focus_evidence_ids: list[UUID] = Field(max_length=64)
    retrieval_key: RetrievalKey | None


@dataclass(frozen=True)
class AppliedPlan:
    idea_version: IdeaVersion | None
    decision: PlannerDecision


class IdeaStateService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = OwnedRepository(session)

    def context(self, *, owner_id: UUID, run_id: UUID) -> PlannerContext:
        run = self.repo.get_run(run_id, owner_id=owner_id)
        if run is None:
            raise LookupError("run not found")
        return self._context(run)

    def _source(self, run: AnalysisRun) -> AnalysisRun | None:
        if run.source_run_id is None:
            return None
        source = self.repo.get_run(run.source_run_id, owner_id=run.owner_user_id)
        if (
            source is None
            or source.conversation_id != run.conversation_id
            or source.status != "completed"
        ):
            raise LookupError("source run not found")
        return source

    def _context(self, run: AnalysisRun) -> PlannerContext:
        base = (
            self.session.get(IdeaVersion, run.base_idea_version_id)
            if run.base_idea_version_id
            else None
        )
        if base is not None and base.conversation_id != run.conversation_id:
            raise LookupError("idea version not found")
        idea = IdeaV1.model_validate_json(json.dumps(base.normalized_json)) if base else None
        source = self._source(run)
        evidence = self.repo.evidence(source.id, owner_id=run.owner_user_id) if source else []
        allowed = tuple(sorted((e.evidence_id for e in evidence), key=str))
        sources = self._source_order(source, evidence) if source else ()
        return PlannerContext(idea, run.expected_idea_version, run.source_run_id, allowed, sources)

    @staticmethod
    def _source_order(
        source: AnalysisRun, evidence: list[RunEvidence]
    ) -> tuple[EvidenceSource, ...]:
        # Порядок берётся только из сохранённого snapshot, никогда из сортировки UUID.
        raw = (source.evidence_snapshot_json or {}).get("sources", [])
        if not isinstance(raw, list) or len(raw) > 64:
            return ()
        result = []
        documents = {str(e.document_id) for e in evidence}
        seen: set[str] = set()
        try:
            for position, item in enumerate(raw, 1):
                document = item["document_id"]
                ids = item["evidence_ids"]
                allowed = {str(e.evidence_id) for e in evidence if str(e.document_id) == document}
                if document not in documents or document in seen or not set(ids) <= allowed:
                    return ()
                seen.add(document)
                result.append(
                    EvidenceSource.model_validate_json(
                        json.dumps(
                            {
                                "ordinal": position,
                                "document_id": document,
                                "title": item["title"],
                                "evidence_ids": ids,
                            }
                        )
                    )
                )
        except (KeyError, TypeError, ValidationError):
            return ()
        return tuple(result)

    def apply(
        self,
        *,
        owner_id: UUID,
        run_id: UUID,
        worker: str,
        lease_token: int,
        plan: PlannerV1,
        generation_id: UUID,
        retrieval_config_hash: str,
        query_hash: str,
    ) -> AppliedPlan:
        # Проверка владельца предшествует чтению и блокировке чужого задания.
        if self.repo.get_run(run_id, owner_id=owner_id) is None:
            raise LookupError("run not found")
        run = JobRepository(self.session).fenced_run(run_id, worker=worker, token=lease_token)
        if run is None:
            raise PlannerFenceLost("PLANNER_FENCE_LOST")
        if run.planner_applied_at is not None:
            decision = PlannerDecision.model_validate_json(
                json.dumps(run.config_versions_json["planner_v1"])
            )
            version = (
                self.session.get(IdeaVersion, run.idea_version_id) if run.idea_version_id else None
            )
            return AppliedPlan(version, decision)

        self.session.scalar(
            select(Conversation)
            .where(
                Conversation.id == run.conversation_id,
                Conversation.owner_user_id == owner_id,
            )
            .with_for_update()
        )
        idea = self.session.scalar(
            select(Idea)
            .where(Idea.conversation_id == run.conversation_id)
            .execution_options(populate_existing=True)
        )
        current_id = idea.current_version_id if idea else None
        current = self.session.get(IdeaVersion, current_id) if current_id else None
        if (
            current_id != run.base_idea_version_id
            or (current.version_no if current else 0) != run.expected_idea_version
        ):
            raise VersionConflict("IDEA_VERSION_CONFLICT")
        context = self._context(run)
        plan = normalize_plan(plan, context)
        source = self._source(run)
        has_evidence = bool(
            source
            and source.evidence_snapshot_json is not None
            and context.allowed_evidence_ids
            and source.idea_version_id
        )
        if plan.intent == "explain_evidence" and not has_evidence:
            plan = clarify(context.version)
        normalized = apply_patch(plan, context)
        key = (
            RetrievalKey(
                state_hash=state_hash(normalized),
                generation_id=generation_id,
                config_hash=retrieval_config_hash,
                query_hash=query_hash,
            )
            if normalized
            else None
        )
        previous = self._previous_key(source)
        retrieval = requires_retrieval(
            plan, current=key, previous=previous, has_evidence=has_evidence
        )
        historical = plan.intent == "explain_evidence"
        reuse = has_evidence and not retrieval and plan.intent != "clarify"
        if historical:
            assert source is not None and source.idea_version_id is not None
            version = self.session.get(IdeaVersion, source.idea_version_id)
        elif plan.has_patch:
            assert normalized is not None
            version = self.repo.apply_idea_version(
                owner_id=owner_id,
                run_id=run.id,
                normalized=normalized.model_dump(mode="json"),
                state_hash=state_hash(normalized),
            )
        else:
            version = current
        if reuse:
            assert source is not None
            self._copy_snapshot(source, run, historical=historical)
        elif retrieval:
            run.index_generation_id = generation_id
        decision = PlannerDecision(
            intent=plan.intent,
            requires_retrieval=retrieval,
            historical=historical,
            source_run_id=source.id if reuse and source else None,
            focus_evidence_ids=list(plan.focus_evidence_ids),
            retrieval_key=previous if historical else key,
        )
        run.idea_version_id = version.id if version else None
        run.planner_applied_at = utcnow()
        run.config_versions_json = {
            **run.config_versions_json,
            "planner_v1": decision.model_dump(mode="json"),
        }
        self.session.flush()
        return AppliedPlan(version, decision)

    @staticmethod
    def _previous_key(source: AnalysisRun | None) -> RetrievalKey | None:
        if source is None:
            return None
        try:
            raw: Any = source.config_versions_json.get("planner_v1", {}).get("retrieval_key")
            return RetrievalKey.model_validate_json(json.dumps(raw))
        except (AttributeError, ValidationError, TypeError, ValueError):
            return None

    def _copy_snapshot(self, source: AnalysisRun, run: AnalysisRun, *, historical: bool) -> None:
        if run.evidence_snapshot_json is not None or self.repo.evidence(
            run.id, owner_id=run.owner_user_id
        ):
            raise VersionConflict("SNAPSHOT_ALREADY_EXISTS")
        run.evidence_snapshot_json = copy.deepcopy(source.evidence_snapshot_json)
        run.index_generation_id = source.index_generation_id
        run.coverage_json = {**copy.deepcopy(source.coverage_json), "historical": historical}
        for item in self.repo.evidence(source.id, owner_id=run.owner_user_id):
            values = {
                column.name: getattr(item, column.name)
                for column in RunEvidence.__table__.columns
                if column.name != "run_id"
            }
            self.session.add(RunEvidence(run_id=run.id, **values))
