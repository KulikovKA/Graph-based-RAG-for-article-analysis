"""Sequential, lease-fenced orchestration of one analysis run.

The progress callback is a typed service boundary. It deliberately has no SSE
or HTTP dependency, so JOB-002 can persist progress and events transactionally.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol, TypeVar
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.contracts import (
    AnalysisV1,
    AnswerPresentationV1,
    AnswerV1,
    CoverageV1,
    PublicAnalysisV1,
)
from app.domain.evidence import CandidateEvidence, RetrievalUnavailable
from app.domain.inference import InferenceCancelled, InferenceConfigurationError
from app.domain.planner import IdeaV1, IntentPlanner, PlannerContext, PlannerResult
from app.services.analyst import (
    PROMPT_VERSION as ANALYST_PROMPT_VERSION,
)
from app.services.analyst import (
    RENDERER_VERSION,
    Analyst,
    AnalystResult,
    AnalystViolation,
    _coverage_limitations,
    _render_analysis,
    _render_fallback,
    validate_analysis,
    validate_projections,
)
from app.services.evidence_pack import (
    EvidencePack,
    EvidencePackItem,
    GemmaTokenCounter,
    build_evidence_pack,
)
from app.services.idea_state import (
    AppliedPlan,
    IdeaStateService,
    PlannerDecision,
    PlannerFenceLost,
)
from app.services.rerank import RankedCandidate
from app.services.retrieval import CandidateRetrievalService
from app.storage.jobs import JobRepository
from app.storage.models import (
    AnalysisRun,
    Conversation,
    DocumentRevision,
    EvidenceChunk,
    IdeaVersion,
    IndexCatalog,
    RunEvidence,
    SourceDocument,
)
from app.storage.repositories import OwnedRepository, VersionConflict

ProgressStage = Literal["planning", "retrieving", "reranking", "analyzing", "verification"]
ProgressPhase = Literal["started", "completed", "waiting"]


@dataclass(frozen=True)
class ProgressCounts:
    feature_count: int | None = None
    candidate_count: int | None = None
    selected_document_count: int | None = None


@dataclass(frozen=True)
class StageProgress:
    attempt: int
    stage: ProgressStage
    phase: ProgressPhase
    stage_started_at: datetime
    counts: ProgressCounts
    idea_version_id: UUID | None = None


class ProgressCallback(Protocol):
    async def __call__(self, update: StageProgress) -> None: ...


class RetryableJobFailure(RuntimeError):
    def __init__(self, error_code: str) -> None:
        self.error_code = error_code
        super().__init__(error_code)


class TerminalJobFailure(RuntimeError):
    def __init__(self, error_code: str) -> None:
        self.error_code = error_code
        super().__init__(error_code)


class LeaseLost(RuntimeError):
    """The worker lost its fencing token; it must discard every late result."""


class RunCancelled(RuntimeError):
    """The current run has a durable cancel request."""


@dataclass(frozen=True)
class AnalysisRunConfig:
    deadline_seconds: float = 1800
    analyst_token_budget: int = 6000
    max_documents: int = 12
    output_tokens: int = 2048

    def __post_init__(self) -> None:
        if self.deadline_seconds <= 0 or self.analyst_token_budget < 1:
            raise ValueError("invalid analysis run budget")
        if not 1 <= self.max_documents <= 15 or not 1 <= self.output_tokens <= 2048:
            raise ValueError("invalid analysis run limits")


RerankFunction = Callable[[str, list[str], str, float, asyncio.Event], Awaitable[Sequence[float]]]
TokenCounter = Callable[[str], int]
T = TypeVar("T")


@dataclass(frozen=True)
class _RunInput:
    run_id: UUID
    owner_id: UUID
    query: str
    message: str
    summary: str
    request_id: str
    context: PlannerContext | None
    applied: AppliedPlan | None
    planner_applied_at: datetime | None
    generation_id: UUID | None
    pack: EvidencePack | None
    coverage: CoverageV1 | None
    snapshot_exists: bool


class AnalysisRunService:
    """Run Planner → retrieval → rerank/pack → Analyst with short DB transactions."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        planner: IntentPlanner,
        retrieval: CandidateRetrievalService,
        analyst: Analyst,
        *,
        rerank: RerankFunction,
        token_counter: TokenCounter | GemmaTokenCounter,
        retrieval_config_hash: str,
        analyst_tokenizer_version: str,
        config: AnalysisRunConfig | None = None,
    ) -> None:
        if len(retrieval_config_hash) != 64 or not analyst_tokenizer_version:
            raise ValueError("retrieval and tokenizer versions are required")
        self.session_factory = session_factory
        self.planner = planner
        self.retrieval = retrieval
        self.analyst = analyst
        self.rerank = rerank
        self.token_counter = token_counter
        self.retrieval_config_hash = retrieval_config_hash
        self.analyst_tokenizer_version = analyst_tokenizer_version
        self.config = config or AnalysisRunConfig()

    async def execute(
        self,
        run_id: UUID,
        *,
        worker: str,
        lease_token: int,
        attempt: int,
        cancel: asyncio.Event,
        progress: ProgressCallback | None = None,
    ) -> AnalystResult:
        deadline = time.monotonic() + self.config.deadline_seconds
        counts = ProgressCounts()
        data = self._read_input(run_id, worker=worker, token=lease_token)
        if data.applied is not None:
            applied = data.applied
            idea = self._idea(applied.idea_version)
            counts = ProgressCounts(feature_count=len(idea.features))
            await self._stage(
                run_id,
                worker,
                lease_token,
                attempt,
                "planning",
                "completed",
                data.planner_applied_at or self._now(),
                counts,
                progress,
                cancel,
                idea_version_id=applied.idea_version.id if applied.idea_version else None,
            )
        else:
            assert data.context is not None
            start = self._now()
            await self._stage(
                run_id,
                worker,
                lease_token,
                attempt,
                "planning",
                "started",
                start,
                counts,
                progress,
                cancel,
            )
            try:
                plan_result = await self.planner.plan(
                    message=data.message,
                    summary=data.summary,
                    context=data.context,
                    request_id=data.request_id,
                    timeout=self._remaining(deadline),
                    cancel=cancel,
                )
            except InferenceCancelled:
                raise RunCancelled("run cancelled during planning") from None
            except InferenceConfigurationError:
                raise TerminalJobFailure("PLANNER_CONFIGURATION_ERROR") from None
            self._check(cancel, deadline)
            applied = self._apply_plan(
                data,
                plan_result,
                worker=worker,
                token=lease_token,
                retrieval_config_hash=self.retrieval_config_hash,
            )
            idea = self._idea(applied.idea_version)
            counts = ProgressCounts(feature_count=len(idea.features))
            await self._stage(
                run_id,
                worker,
                lease_token,
                attempt,
                "planning",
                "completed",
                start,
                counts,
                progress,
                cancel,
                idea_version_id=applied.idea_version.id if applied.idea_version else None,
            )
            data = self._read_input(run_id, worker=worker, token=lease_token)

        self._check(cancel, deadline)
        applied = self._reload_applied(run_id, worker=worker, token=lease_token, fallback=applied)
        idea = self._idea(applied.idea_version)
        counts = ProgressCounts(feature_count=len(idea.features))
        decision = applied.decision
        pack = data.pack
        coverage = data.coverage

        if data.snapshot_exists:
            if pack is None or coverage is None:
                raise TerminalJobFailure("INVALID_EVIDENCE_SNAPSHOT")
            counts = ProgressCounts(
                feature_count=len(idea.features),
                selected_document_count=len({item.document_id for item in pack.items}),
            )
        elif decision.requires_retrieval:
            generation_id = decision.retrieval_key.generation_id if decision.retrieval_key else None
            if generation_id is None:
                raise TerminalJobFailure("INDEX_GENERATION_UNAVAILABLE")
            request_id = data.request_id
            started = self._now()
            await self._stage(
                run_id,
                worker,
                lease_token,
                attempt,
                "retrieving",
                "started",
                started,
                counts,
                progress,
                cancel,
                idea_version_id=applied.idea_version.id if applied.idea_version else None,
            )
            try:
                retrieval = await self._within_deadline(
                    self.retrieval.search(
                        original_query=data.query,
                        idea=idea,
                        generation_id=generation_id,
                        request_id=request_id,
                    ),
                    deadline,
                )
            except asyncio.CancelledError:
                if cancel.is_set():
                    raise RunCancelled("run cancelled during retrieval") from None
                raise
            except TimeoutError:
                raise RetryableJobFailure("RETRIEVAL_TIMEOUT") from None
            except InferenceCancelled:
                raise RunCancelled("run cancelled during retrieval") from None
            except InferenceConfigurationError:
                raise TerminalJobFailure("RETRIEVAL_CONFIGURATION_ERROR") from None
            except Exception as exc:
                if isinstance(exc, RetrievalUnavailable):
                    raise RetryableJobFailure("RETRIEVAL_UNAVAILABLE") from None
                raise
            self._check(cancel, deadline)
            counts = ProgressCounts(
                feature_count=len(idea.features), candidate_count=len(retrieval.candidates)
            )
            await self._stage(
                run_id,
                worker,
                lease_token,
                attempt,
                "retrieving",
                "completed",
                started,
                counts,
                progress,
                cancel,
                idea_version_id=applied.idea_version.id if applied.idea_version else None,
            )
            ranked: tuple[RankedCandidate, ...] = ()
            reranking_started: datetime | None = None
            if retrieval.candidates:
                reranking_started = self._now()
                await self._stage(
                    run_id,
                    worker,
                    lease_token,
                    attempt,
                    "reranking",
                    "started",
                    reranking_started,
                    counts,
                    progress,
                    cancel,
                )
                try:
                    scores = await self._within_deadline(
                        self.rerank(
                            data.query,
                            [
                                f"{item.title}\n{item.section}\n{item.text}"
                                for item in retrieval.candidates
                            ],
                            request_id,
                            self._remaining(deadline),
                            cancel,
                        ),
                        deadline,
                    )
                    from app.services.rerank import _ordered

                    ranked = _ordered(retrieval.candidates, scores, 15)
                except asyncio.CancelledError:
                    if cancel.is_set():
                        raise RunCancelled("run cancelled during reranking") from None
                    raise
                except TimeoutError:
                    raise RetryableJobFailure("RERANK_TIMEOUT") from None
                except InferenceCancelled:
                    raise RunCancelled("run cancelled during reranking") from None
                except InferenceConfigurationError:
                    raise TerminalJobFailure("RERANKER_CONFIGURATION_ERROR") from None
                except (OSError, RuntimeError):
                    raise RetryableJobFailure("RERANKER_UNAVAILABLE") from None
                self._check(cancel, deadline)
            coverage = retrieval.coverage
            if not idea.features:
                pack = EvidencePack((), 0, self.config.analyst_token_budget)
            else:
                pack = self._build_pack(idea, coverage, ranked, data.query)
            counts = ProgressCounts(
                feature_count=len(idea.features),
                candidate_count=len(retrieval.candidates),
                selected_document_count=len({item.document_id for item in pack.items}),
            )
            if reranking_started is not None:
                await self._stage(
                    run_id,
                    worker,
                    lease_token,
                    attempt,
                    "reranking",
                    "completed",
                    reranking_started,
                    counts,
                    progress,
                    cancel,
                )
            snapshot, rows = self._snapshot(
                pack, retrieval.candidates, generation_id, len(retrieval.candidates)
            )
            if not self._save_snapshot(
                run_id,
                worker=worker,
                token=lease_token,
                snapshot=snapshot,
                evidence=rows,
                coverage=coverage,
                generation_id=generation_id,
            ):
                raise LeaseLost("lease lost before evidence snapshot commit")
            data = _RunInput(
                **{**data.__dict__, "pack": pack, "coverage": coverage, "snapshot_exists": True}
            )
        elif pack is None:
            pack = EvidencePack((), 0, self.config.analyst_token_budget)
            coverage = coverage or self._empty_coverage(decision.historical)

        self._check(cancel, deadline)
        assert pack is not None
        coverage = coverage or self._empty_coverage(decision.historical)
        if decision.intent == "clarify":
            # Analyst's empty-idea path is deterministic and cannot expose the user draft.
            idea = IdeaV1(features=[])
            pack = EvidencePack((), 0, self.config.analyst_token_budget)
        start = self._now()
        await self._stage(
            run_id,
            worker,
            lease_token,
            attempt,
            "analyzing",
            "started",
            start,
            counts,
            progress,
            cancel,
        )
        try:
            result = await self.analyst.analyze(
                idea=idea,
                pack=pack,
                coverage=coverage,
                request_id=data.request_id,
                timeout=self._remaining(deadline),
                max_output_tokens=self.config.output_tokens,
                cancel=cancel,
            )
        except InferenceCancelled:
            raise RunCancelled("run cancelled during Analyst inference") from None
        except InferenceConfigurationError:
            raise TerminalJobFailure("ANALYST_CONFIGURATION_ERROR") from None
        self._check(cancel, deadline)
        await self._stage(
            run_id,
            worker,
            lease_token,
            attempt,
            "analyzing",
            "completed",
            start,
            counts,
            progress,
            cancel,
        )

        verification_started = self._now()
        await self._stage(
            run_id,
            worker,
            lease_token,
            attempt,
            "verification",
            "started",
            verification_started,
            counts,
            progress,
            cancel,
        )
        result = self._verify_result(result, idea=idea, pack=pack, coverage=coverage)
        self._check(cancel, deadline)
        if not self._record_runtime_versions(run_id, worker, lease_token):
            raise LeaseLost("lease lost before result commit")
        await self._stage(
            run_id,
            worker,
            lease_token,
            attempt,
            "verification",
            "completed",
            verification_started,
            counts,
            progress,
            cancel,
        )
        return result

    def _read_input(self, run_id: UUID, *, worker: str, token: int) -> _RunInput:
        with self.session_factory() as session, session.begin():
            repo = JobRepository(session)
            run = repo.fenced_run(run_id, worker=worker, token=token)
            if run is None:
                raise LeaseLost("lease not held")
            message = OwnedRepository(session).get_message(
                run.message_id, owner_id=run.owner_user_id
            )
            if message is None:
                raise TerminalJobFailure("RUN_MESSAGE_NOT_FOUND")
            conversation = session.get(Conversation, run.conversation_id)
            summary = ""
            if conversation and isinstance(conversation.summary_json, dict):
                value = conversation.summary_json.get("text", "")
                if isinstance(value, str):
                    summary = value[:4000]
            applied = None
            context = None
            generation_id = run.index_generation_id
            if run.planner_applied_at is not None:
                try:
                    decision = PlannerDecision.model_validate(
                        run.config_versions_json["planner_v1"]
                    )
                    version = (
                        session.get(IdeaVersion, run.idea_version_id)
                        if run.idea_version_id is not None
                        else None
                    )
                except (KeyError, TypeError, ValidationError):
                    raise TerminalJobFailure("INVALID_PLANNER_SNAPSHOT") from None
                applied = AppliedPlan(version, decision)
                generation_id = (
                    decision.retrieval_key.generation_id
                    if decision.retrieval_key
                    else generation_id
                )
            else:
                context = IdeaStateService(session).context(
                    owner_id=run.owner_user_id, run_id=run.id
                )
                catalog = session.get(IndexCatalog, 1)
                generation_id = catalog.current_generation_id if catalog else None
            snapshot_exists = run.evidence_snapshot_json is not None
            pack = self._load_pack(session, run) if snapshot_exists else None
            coverage = self._coverage(run.coverage_json) if snapshot_exists else None
            return _RunInput(
                run_id=run.id,
                owner_id=run.owner_user_id,
                query=run.query,
                message=message.content,
                summary=summary,
                request_id=str(run.id),
                context=context,
                applied=applied,
                planner_applied_at=run.planner_applied_at,
                generation_id=generation_id,
                pack=pack,
                coverage=coverage,
                snapshot_exists=snapshot_exists,
            )

    def _apply_plan(
        self,
        data: _RunInput,
        result: PlannerResult,
        *,
        worker: str,
        token: int,
        retrieval_config_hash: str,
    ) -> AppliedPlan:
        if data.generation_id is None:
            raise TerminalJobFailure("INDEX_GENERATION_UNAVAILABLE")
        try:
            with self.session_factory() as session, session.begin():
                return IdeaStateService(session).apply(
                    owner_id=data.owner_id,
                    run_id=data.run_id,
                    worker=worker,
                    lease_token=token,
                    plan=result.plan,
                    generation_id=data.generation_id,
                    retrieval_config_hash=retrieval_config_hash,
                    query_hash=hashlib.sha256(data.query.encode("utf-8")).hexdigest(),
                )
        except PlannerFenceLost:
            raise LeaseLost("lease lost applying Planner CAS") from None
        except VersionConflict:
            raise TerminalJobFailure("IDEA_VERSION_CONFLICT") from None

    def _reload_applied(
        self, run_id: UUID, *, worker: str, token: int, fallback: AppliedPlan
    ) -> AppliedPlan:
        with self.session_factory() as session, session.begin():
            run = JobRepository(session).fenced_run(run_id, worker=worker, token=token)
            if run is None:
                raise LeaseLost("lease lost after Planner CAS")
            if run.planner_applied_at is None:
                return fallback
            try:
                decision = PlannerDecision.model_validate(run.config_versions_json["planner_v1"])
            except (KeyError, TypeError, ValidationError):
                raise TerminalJobFailure("INVALID_PLANNER_SNAPSHOT") from None
            version = session.get(IdeaVersion, run.idea_version_id) if run.idea_version_id else None
            return AppliedPlan(version, decision)

    def _load_pack(self, session: Session, run: AnalysisRun) -> EvidencePack:
        snapshot = run.evidence_snapshot_json or {}
        raw = snapshot.get("evidence", []) if isinstance(snapshot, dict) else []
        items: list[EvidencePackItem] = []
        if isinstance(raw, list) and raw:
            try:
                items = []
                uuid_fields = ("evidence_id", "document_id", "revision_id", "chunk_id")
                for entry in raw:
                    values = dict(entry)
                    for field in uuid_fields:
                        values[field] = UUID(str(values[field]))
                    values["retrieval_score"] = float(values["retrieval_score"])
                    values["rerank_score"] = float(values["rerank_score"])
                    items.append(EvidencePackItem(**values))
            except (TypeError, ValidationError, ValueError):
                if isinstance(snapshot, dict) and "evidence" in snapshot:
                    raise TerminalJobFailure("INVALID_EVIDENCE_SNAPSHOT") from None
        rows = session.execute(
            select(RunEvidence, EvidenceChunk, DocumentRevision, SourceDocument)
            .join(EvidenceChunk, EvidenceChunk.id == RunEvidence.chunk_id)
            .join(DocumentRevision, DocumentRevision.id == RunEvidence.revision_id)
            .join(SourceDocument, SourceDocument.id == RunEvidence.document_id)
            .where(RunEvidence.run_id == run.id)
            .order_by(SourceDocument.source, SourceDocument.external_id, RunEvidence.evidence_id)
        ).all()
        if not items:
            if raw or (isinstance(snapshot, dict) and "evidence" in snapshot and rows):
                raise TerminalJobFailure("INVALID_EVIDENCE_SNAPSHOT")
            source_meta = (
                {
                    entry.get("document_id"): entry
                    for entry in snapshot.get("sources", [])
                    if isinstance(entry, dict) and isinstance(entry.get("document_id"), str)
                }
                if isinstance(snapshot, dict)
                else {}
            )
            for evidence, chunk, _revision, document in rows:
                meta = source_meta.get(str(document.id), {})
                items.append(
                    EvidencePackItem(
                        evidence_id=evidence.evidence_id,
                        document_id=evidence.document_id,
                        revision_id=evidence.revision_id,
                        chunk_id=evidence.chunk_id,
                        source=document.source,
                        external_id=document.external_id,
                        canonical_url=evidence.source_url,
                        title=meta.get("title", document.title),
                        section=chunk.section,
                        language=chunk.language,
                        span_start=evidence.span_start,
                        span_end=evidence.span_end,
                        quoted_span=evidence.quoted_span,
                        retrieval_score=evidence.retrieval_score or 0.0,
                        rerank_score=evidence.rerank_score or 0.0,
                    )
                )
        rows_by_id = {evidence.evidence_id: (evidence, chunk) for evidence, chunk, _, _ in rows}
        if len(rows_by_id) != len(rows) or len({item.evidence_id for item in items}) != len(items):
            raise TerminalJobFailure("INVALID_EVIDENCE_SNAPSHOT")
        for item in items:
            persisted = rows_by_id.get(item.evidence_id)
            if persisted is None:
                raise TerminalJobFailure("INVALID_EVIDENCE_SNAPSHOT")
            evidence, chunk = persisted
            if (
                item.document_id != evidence.document_id
                or item.revision_id != evidence.revision_id
                or item.chunk_id != evidence.chunk_id
                or item.span_start != evidence.span_start
                or item.span_end != evidence.span_end
                or item.quoted_span != evidence.quoted_span
                or item.canonical_url != evidence.source_url
                or item.section != chunk.section
                or item.language != chunk.language
                or chunk.text[item.span_start : item.span_end] != item.quoted_span
            ):
                raise TerminalJobFailure("INVALID_EVIDENCE_SNAPSHOT")
        if len(items) != len(rows):
            raise TerminalJobFailure("INVALID_EVIDENCE_SNAPSHOT")
        count = self._count_prompt_tokens(
            self._idea_for_run(session, run), self._coverage(run.coverage_json), items
        )
        return EvidencePack(tuple(items), count, self.config.analyst_token_budget)

    def _idea_for_run(self, session: Session, run: AnalysisRun) -> IdeaV1:
        version = session.get(IdeaVersion, run.idea_version_id) if run.idea_version_id else None
        return self._idea(version)

    @staticmethod
    def _idea(version: IdeaVersion | None) -> IdeaV1:
        if version is None:
            return IdeaV1(features=[])
        try:
            return IdeaV1.model_validate(version.normalized_json)
        except ValidationError:
            raise TerminalJobFailure("INVALID_IDEA_SNAPSHOT") from None

    @staticmethod
    def _coverage(value: dict[str, object] | None) -> CoverageV1:
        if not isinstance(value, dict) or not value:
            return AnalysisRunService._empty_coverage(False)
        try:
            return CoverageV1.model_validate(value)
        except ValidationError:
            raise TerminalJobFailure("INVALID_COVERAGE_SNAPSHOT") from None

    @staticmethod
    def _empty_coverage(historical: bool) -> CoverageV1:
        return CoverageV1(sources=[], channels=[], partial=False, historical=historical)

    def _build_pack(
        self,
        idea: IdeaV1,
        coverage: CoverageV1,
        ranked: Sequence[RankedCandidate],
        query: str,
    ) -> EvidencePack:
        def count_full_prompt(rendered_pack: str) -> int:
            try:
                evidence = json.loads(rendered_pack) if rendered_pack else []
            except (ValueError, TypeError):
                raise ValueError("invalid Analyst evidence JSON") from None
            input_json = json.dumps(
                {
                    "idea": idea.model_dump(mode="json"),
                    "coverage": coverage.model_dump(mode="json"),
                    "evidence_pack": evidence,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                default=str,
            )
            prompt = self.analyst.prompt.replace(
                "{schema_json}",
                json.dumps(
                    AnalysisV1.model_json_schema(), ensure_ascii=False, separators=(",", ":")
                ),
            ).replace("{input_json}", input_json)
            return self.token_counter(prompt)

        return build_evidence_pack(
            ranked,
            query=query,
            token_counter=count_full_prompt,
            token_budget=self.config.analyst_token_budget,
            max_documents=self.config.max_documents,
        )

    @staticmethod
    def _snapshot(
        pack: EvidencePack,
        candidates: Sequence[CandidateEvidence],
        generation_id: UUID,
        candidate_count: int,
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        by_document = {str(item.document_id): item for item in candidates}
        sources: dict[str, dict[str, object]] = {}
        evidence_dump: list[dict[str, object]] = []
        rows: list[dict[str, object]] = []
        for item in pack.items:
            document_id = str(item.document_id)
            candidate = by_document.get(document_id)
            if candidate is None:
                raise TerminalJobFailure("EVIDENCE_CANDIDATE_MISMATCH")
            source = sources.setdefault(
                document_id,
                {
                    "document_id": document_id,
                    "revision_id": str(item.revision_id),
                    "title": item.title,
                    "kind": candidate.kind,
                    "publication_date": (
                        candidate.publication_date.isoformat()
                        if candidate.publication_date
                        else None
                    ),
                    "url": item.canonical_url,
                    "evidence_ids": [],
                },
            )
            evidence_ids = source["evidence_ids"]
            assert isinstance(evidence_ids, list)
            evidence_ids.append(str(item.evidence_id))
            evidence_dump.append(
                {
                    **json.loads(json.dumps(asdict(item), default=str)),
                    "source": item.source,
                    "external_id": item.external_id,
                }
            )
            rows.append(
                {
                    "evidence_id": item.evidence_id,
                    "document_id": item.document_id,
                    "revision_id": item.revision_id,
                    "chunk_id": item.chunk_id,
                    "span_start": item.span_start,
                    "span_end": item.span_end,
                    "quoted_span": item.quoted_span,
                    "source_url": item.canonical_url,
                    "retrieval_score": item.retrieval_score,
                    "rerank_score": item.rerank_score,
                    "index_generation_id": generation_id,
                }
            )
        snapshot = {
            "schema_version": 1,
            "generation_id": str(generation_id),
            "candidate_count": candidate_count,
            "sources": list(sources.values()),
            "evidence": evidence_dump,
        }
        return snapshot, rows

    def _save_snapshot(
        self,
        run_id: UUID,
        *,
        worker: str,
        token: int,
        snapshot: dict[str, object],
        evidence: list[dict[str, object]],
        coverage: CoverageV1,
        generation_id: UUID,
    ) -> bool:
        with self.session_factory() as session, session.begin():
            return JobRepository(session).save_evidence_snapshot(
                run_id,
                worker=worker,
                token=token,
                snapshot=snapshot,
                evidence=evidence,
                coverage=coverage.model_dump(mode="json"),
                generation_id=generation_id,
            )

    def _record_runtime_versions(self, run_id: UUID, worker: str, token: int) -> bool:
        planner_model = self.planner.model_id
        analyst_model = self.analyst.model_id
        revisions = getattr(self.analyst.provider, "model_revisions", {})
        versions = {
            "publication_contract": "adr011",
            "analysis_pipeline_v1": {
                "retrieval_config_hash": self.retrieval_config_hash,
                "analyst_tokenizer_version": self.analyst_tokenizer_version,
                "analyst_token_budget": self.config.analyst_token_budget,
                "deadline_seconds": self.config.deadline_seconds,
                "planner_model_id": planner_model,
                "planner_prompt_version": "planner_v1",
                "analyst_model_id": analyst_model,
                "analyst_model_revision": revisions.get(analyst_model),
                "analyst_prompt_version": ANALYST_PROMPT_VERSION,
                "analysis_schema_version": 1,
                "validator_version": "analyst_validator_v1",
                "renderer_version": RENDERER_VERSION,
                "reasoning_effort": "low",
                "output_tokens": self.config.output_tokens,
            },
        }
        with self.session_factory() as session, session.begin():
            return JobRepository(session).update_config_versions(
                run_id, worker=worker, token=token, patch=versions
            )

    def _verify_result(
        self,
        result: AnalystResult,
        *,
        idea: IdeaV1,
        pack: EvidencePack,
        coverage: CoverageV1,
    ) -> AnalystResult:
        try:
            answer = AnswerV1.model_validate(result.answer.model_dump(mode="python"))
            public = PublicAnalysisV1.model_validate(
                result.public_analysis.model_dump(mode="python")
            )
            presentation = AnswerPresentationV1.model_validate(
                result.presentation.model_dump(mode="python")
            )
            if result.outcome == "analysis":
                if result.analysis is None:
                    raise AnalystViolation("MISSING_ANALYSIS")
                validate_analysis(result.analysis, idea=idea, pack=pack)
                expected = _render_analysis(result.analysis, idea, coverage)
            elif result.outcome == "safe_fallback":
                if result.analysis is not None or not pack.items:
                    raise AnalystViolation("INVALID_SAFE_FALLBACK_INPUT")
                expected = _render_fallback(idea, pack, coverage)
            elif result.outcome in ("no_evidence", "clarification"):
                if result.analysis is not None or pack.items:
                    raise AnalystViolation("INVALID_EMPTY_RESULT_INPUT")
                if result.outcome == "clarification" and idea.features:
                    raise AnalystViolation("CLARIFICATION_WITH_UNRESOLVED_IDEA")
                if result.outcome == "no_evidence" and not idea.features:
                    raise AnalystViolation("NO_EVIDENCE_WITHOUT_IDEA")
                expected = (
                    AnswerV1(
                        summary=[],
                        matches=[],
                        differences=[],
                        limitations=_coverage_limitations(coverage),
                        followup_suggestions=[],
                    ),
                    PublicAnalysisV1(items=[], limitations=_coverage_limitations(coverage)),
                    result.presentation,
                )
                validate_projections(answer, public, presentation)
                if (
                    answer.summary
                    or answer.matches
                    or answer.differences
                    or answer.followup_suggestions
                ):
                    raise AnalystViolation("EMPTY_RESULT_HAS_FINDINGS")
                if answer.limitations != _coverage_limitations(coverage):
                    raise AnalystViolation("EMPTY_RESULT_LIMITATIONS_MISMATCH")
            else:
                raise AnalystViolation("INVALID_OUTCOME")
            if result.outcome in ("analysis", "safe_fallback") and (
                answer != expected[0] or public != expected[1] or presentation != expected[2]
            ):
                raise AnalystViolation("RESULT_PROJECTION_MISMATCH")
            validate_projections(answer, public, presentation)
        except (AttributeError, TypeError, ValueError, ValidationError) as exc:
            code = str(exc) if isinstance(exc, AnalystViolation) else "INVALID_ANALYST_RESULT"
            raise TerminalJobFailure(
                "INVALID_FALLBACK" if result.outcome == "safe_fallback" else code
            ) from None
        return AnalystResult(
            outcome=result.outcome,
            analysis=result.analysis,
            answer=answer,
            public_analysis=public,
            presentation=presentation,
            attempts=result.attempts,
            diagnostic_codes=result.diagnostic_codes,
            metadata=result.metadata,
        )

    async def _stage(
        self,
        run_id: UUID,
        worker: str,
        token: int,
        attempt: int,
        stage: ProgressStage,
        phase: ProgressPhase,
        stage_started_at: datetime,
        counts: ProgressCounts,
        callback: ProgressCallback | None,
        cancel: asyncio.Event,
        *,
        idea_version_id: UUID | None = None,
    ) -> None:
        self._check(cancel, None)
        if phase == "started":
            with self.session_factory() as session, session.begin():
                if not JobRepository(session).set_stage(
                    run_id, worker=worker, token=token, stage=stage
                ):
                    raise LeaseLost("lease lost updating stage")
        if callback is not None:
            await callback(
                StageProgress(
                    attempt=attempt,
                    stage=stage,
                    phase=phase,
                    stage_started_at=stage_started_at,
                    counts=counts,
                    idea_version_id=idea_version_id,
                )
            )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _remaining(deadline: float) -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TerminalJobFailure("RUN_DEADLINE_EXCEEDED")
        return remaining

    async def _within_deadline(self, awaitable: Awaitable[T], deadline: float) -> T:
        try:
            return await asyncio.wait_for(awaitable, timeout=self._remaining(deadline))
        except TimeoutError:
            raise

    def _count_prompt_tokens(
        self, idea: IdeaV1, coverage: CoverageV1, items: Sequence[EvidencePackItem]
    ) -> int:
        evidence = json.dumps(
            [item.__dict__ for item in items],
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
        # Same construction as Analyst and _build_pack; only known snapshots reach here.
        input_json = json.dumps(
            {
                "idea": idea.model_dump(mode="json"),
                "coverage": coverage.model_dump(mode="json"),
                "evidence_pack": json.loads(evidence),
            },
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
        prompt = self.analyst.prompt.replace(
            "{schema_json}",
            json.dumps(AnalysisV1.model_json_schema(), ensure_ascii=False, separators=(",", ":")),
        ).replace("{input_json}", input_json)
        return self.token_counter(prompt)

    @staticmethod
    def _check(cancel: asyncio.Event, deadline: float | None) -> None:
        if cancel.is_set():
            raise RunCancelled("run cancellation requested")
        if deadline is not None and time.monotonic() >= deadline:
            raise TerminalJobFailure("RUN_DEADLINE_EXCEEDED")
