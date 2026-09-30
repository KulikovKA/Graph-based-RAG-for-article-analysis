"""Закрытый контракт planner и детерминированные правила изменения идеи."""

import asyncio
import hashlib
import json
import time
import unicodedata
from dataclasses import dataclass
from typing import Annotated, Any, Literal, Self
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

from app.domain.inference import (
    InferenceCancelled,
    InferenceConfigurationError,
    InferenceError,
    InferenceProtocolError,
    InferenceProvider,
)

PROMPT_VERSION = "planner_v1"
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Intent = Literal["new_idea", "modify_idea", "explain_evidence", "clarify", "general_followup"]


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)


class FeatureV1(ClosedModel):
    id: UUID
    text: Text
    normalized_term: Text | None = None
    weight: float = Field(default=1.0, gt=0, le=100)


class IdeaV1(ClosedModel):
    schema_version: Literal[1] = 1
    domain: Text = "unspecified"
    features: list[FeatureV1] = Field(max_length=64)
    technologies: list[Text] = Field(default_factory=list, max_length=64)
    constraints: list[Text] = Field(default_factory=list, max_length=64)
    language: Text = "und"

    @model_validator(mode="after")
    def unique_features(self) -> Self:
        if len({f.id for f in self.features}) != len(self.features):
            raise ValueError("DUPLICATE_FEATURE_ID")
        return self


class AddFeature(ClosedModel):
    text: Text
    rationale: Text


class ReplaceFeature(AddFeature):
    feature_id: UUID


class PlannerV1(ClosedModel):
    schema_version: Literal[1]
    intent: Intent
    base_idea_version: int = Field(ge=0)
    add_features: list[AddFeature] = Field(max_length=64)
    remove_feature_ids: list[UUID] = Field(max_length=64)
    replace_features: list[ReplaceFeature] = Field(max_length=64)
    focus_evidence_ids: list[UUID] = Field(max_length=64)
    suggested_retrieval: bool
    confidence: float = Field(ge=0, le=1)

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_schema_version(cls, value: Any) -> Any:
        if type(value) is not int:
            raise ValueError("INVALID_SCHEMA_VERSION")
        return value

    @property
    def has_patch(self) -> bool:
        return bool(self.add_features or self.remove_feature_ids or self.replace_features)

    @model_validator(mode="after")
    def patch_shape(self) -> Self:
        removed = set(self.remove_feature_ids)
        replaced = {f.feature_id for f in self.replace_features}
        if len(removed) != len(self.remove_feature_ids) or len(replaced) != len(
            self.replace_features
        ):
            raise ValueError("DUPLICATE_FEATURE_ID")
        if removed & replaced:
            raise ValueError("OVERLAPPING_PATCH")
        if len(set(self.focus_evidence_ids)) != len(self.focus_evidence_ids):
            raise ValueError("DUPLICATE_EVIDENCE_ID")
        if self.intent not in ("new_idea", "modify_idea") and self.has_patch:
            raise ValueError("PATCH_NOT_ALLOWED")
        if self.intent == "new_idea" and (
            not self.add_features or self.remove_feature_ids or self.replace_features
        ):
            raise ValueError("NEW_IDEA_REQUIRES_FEATURES")
        if self.intent == "modify_idea" and not self.has_patch:
            raise ValueError("EMPTY_PATCH")
        if self.focus_evidence_ids and self.intent not in ("explain_evidence", "general_followup"):
            raise ValueError("FOCUS_NOT_ALLOWED")
        return self


class PlannerViolation(ValueError):
    """Диагностический код без пользовательского текста и вывода модели."""


class EvidenceSource(ClosedModel):
    ordinal: int = Field(ge=1)
    document_id: UUID
    title: Text
    evidence_ids: list[UUID] = Field(min_length=1, max_length=64)


@dataclass(frozen=True)
class PlannerContext:
    idea: IdeaV1 | None
    version: int
    source_run_id: UUID | None = None
    allowed_evidence_ids: tuple[UUID, ...] = ()
    sources: tuple[EvidenceSource, ...] = ()

    def __post_init__(self) -> None:
        if self.version < 0 or (self.idea is None) != (self.version == 0):
            raise ValueError("INVALID_IDEA_CONTEXT")
        if self.allowed_evidence_ids and self.source_run_id is None:
            raise ValueError("INVALID_SOURCE_CONTEXT")
        if any(not set(s.evidence_ids) <= set(self.allowed_evidence_ids) for s in self.sources):
            raise ValueError("INVALID_SOURCE_CONTEXT")


def validate_plan(plan: PlannerV1, context: PlannerContext) -> None:
    if plan.base_idea_version != context.version:
        raise PlannerViolation("IDEA_VERSION_CONFLICT")
    if plan.intent == "new_idea" and context.idea is not None:
        raise PlannerViolation("NEW_CONVERSATION_REQUIRED")
    if plan.intent == "modify_idea" and context.idea is None:
        raise PlannerViolation("IDEA_REQUIRED")
    known = {f.id for f in context.idea.features} if context.idea else set()
    affected = set(plan.remove_feature_ids) | {f.feature_id for f in plan.replace_features}
    if not affected <= known:
        raise PlannerViolation("UNKNOWN_FEATURE_ID")
    if not set(plan.focus_evidence_ids) <= set(context.allowed_evidence_ids):
        raise PlannerViolation("UNKNOWN_EVIDENCE_ID")
    count = len(known) - len(plan.remove_feature_ids) + len(plan.add_features)
    if count > 64:
        raise PlannerViolation("TOO_MANY_FEATURES")


def clarify(version: int) -> PlannerV1:
    return PlannerV1(
        schema_version=1,
        intent="clarify",
        base_idea_version=version,
        add_features=[],
        remove_feature_ids=[],
        replace_features=[],
        focus_evidence_ids=[],
        suggested_retrieval=False,
        confidence=0.0,
    )


def normalize_plan(plan: PlannerV1, context: PlannerContext) -> PlannerV1:
    validate_plan(plan, context)
    if plan.intent == "general_followup" and context.idea is None:
        return clarify(context.version)
    if plan.intent == "explain_evidence" and (
        context.source_run_id is None or not plan.focus_evidence_ids
    ):
        return clarify(context.version)
    return plan


def apply_patch(plan: PlannerV1, context: PlannerContext) -> IdeaV1 | None:
    validate_plan(plan, context)
    if not plan.has_patch:
        return context.idea
    idea = context.idea or IdeaV1(features=[])
    replacements = {f.feature_id: f for f in plan.replace_features}
    features = []
    for feature in idea.features:
        if feature.id in plan.remove_feature_ids:
            continue
        replacement = replacements.get(feature.id)
        if replacement is not None and replacement.text != feature.text:
            # Старый normalized_term не должен описывать уже заменённый признак.
            feature = FeatureV1(id=feature.id, text=replacement.text, weight=feature.weight)
        features.append(feature)
    features.extend(FeatureV1(id=uuid4(), text=f.text) for f in plan.add_features)
    return IdeaV1(
        domain=idea.domain,
        features=features,
        technologies=list(idea.technologies),
        constraints=list(idea.constraints),
        language=idea.language,
    )


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def state_hash(idea: IdeaV1) -> str:
    def normalized(text: str) -> str:
        return " ".join(unicodedata.normalize("NFC", text).split())

    features = [
        {
            "text": normalized(f.text),
            "normalized_term": normalized(f.normalized_term) if f.normalized_term else None,
            "weight": f.weight,
        }
        for f in idea.features
    ]
    return canonical_hash(
        {
            "schema_version": idea.schema_version,
            "domain": normalized(idea.domain),
            "features": sorted(features, key=lambda f: json.dumps(f, sort_keys=True)),
            "technologies": sorted(normalized(t) for t in idea.technologies),
            "constraints": sorted(normalized(t) for t in idea.constraints),
            "language": normalized(idea.language),
        }
    )


class RetrievalKey(ClosedModel):
    state_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    generation_id: UUID
    config_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    query_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


def requires_retrieval(
    plan: PlannerV1,
    *,
    current: RetrievalKey | None,
    previous: RetrievalKey | None,
    has_evidence: bool,
) -> bool:
    """Вызывать после normalize_plan; suggested_retrieval намеренно не используется."""
    if plan.intent in ("clarify", "explain_evidence"):
        return False
    return not (has_evidence and current is not None and current == previous)


@dataclass(frozen=True)
class PlannerResult:
    plan: PlannerV1
    attempts: int
    diagnostic_codes: tuple[str, ...] = ()


def _schema_codes(error: ValidationError) -> list[str]:
    allowed = set(PlannerV1.model_fields) | set(ReplaceFeature.model_fields)
    codes = []
    for item in error.errors(include_input=False, include_context=False, include_url=False)[:8]:
        path = ".".join(
            str(part) if isinstance(part, int) or part in allowed else "field"
            for part in item["loc"]
        )
        codes.append(f"INVALID_SCHEMA:{item['type']}:{path}")
    return codes


class IntentPlanner:
    """InferenceProvider уже владеет общим generation gate и остановкой backend."""

    def __init__(self, provider: InferenceProvider, *, model_id: str, prompt: str) -> None:
        self.provider = provider
        self.model_id = model_id
        self.prompt = prompt

    async def plan(
        self,
        *,
        message: str,
        context: PlannerContext,
        request_id: str,
        timeout: float,
        summary: str = "",
        cancel: asyncio.Event | None = None,
    ) -> PlannerResult:
        if not message.strip() or len(message) > 16000 or len(summary) > 4000 or timeout <= 0:
            raise ValueError("INVALID_PLANNER_INPUT")
        payload = {
            "message": message,
            "summary": summary,
            "idea": context.idea.model_dump(mode="json") if context.idea else None,
            "idea_version": context.version,
            "source_run_id": str(context.source_run_id) if context.source_run_id else None,
            "allowed_evidence_ids": [str(e) for e in context.allowed_evidence_ids],
            "sources": [source.model_dump(mode="json") for source in context.sources],
        }
        original = self.prompt + "\nINPUT_JSON:\n" + json.dumps(payload, ensure_ascii=False)
        prompt = original
        deadline = time.monotonic() + timeout
        codes: list[str] = []
        for attempt in (1, 2):
            if cancel is not None and cancel.is_set():
                raise InferenceCancelled("planner cancelled")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return PlannerResult(clarify(context.version), attempt - 1, ("DEADLINE",))
            try:
                result = await self.provider.complete_json(
                    model_id=self.model_id,
                    prompt_version=PROMPT_VERSION,
                    request_id=request_id,
                    prompt=prompt,
                    timeout=remaining,
                    schema=PlannerV1.model_json_schema(),
                    max_output_tokens=4096,
                    cancel=cancel,
                )
                if cancel is not None and cancel.is_set():
                    raise InferenceCancelled("planner cancelled")
                if time.monotonic() >= deadline:
                    return PlannerResult(clarify(context.version), attempt, ("DEADLINE",))
                raw = json.dumps(result.value, ensure_ascii=False, allow_nan=False)
                if len(raw.encode("utf-8")) > 65536:
                    raise PlannerViolation("OUTPUT_TOO_LARGE")
                plan = PlannerV1.model_validate_json(raw)
                plan = normalize_plan(plan, context)
                return PlannerResult(plan, attempt, tuple(codes))
            except (InferenceCancelled, InferenceConfigurationError):
                raise
            except ValidationError as exc:
                codes.extend(_schema_codes(exc))
            except PlannerViolation as exc:
                codes.append(str(exc))
            except InferenceProtocolError:
                codes.append("INVALID_PROVIDER_JSON")
            except InferenceError:
                return PlannerResult(clarify(context.version), attempt, ("INFERENCE_UNAVAILABLE",))
            except (TypeError, ValueError):
                codes.append("INVALID_JSON")
            # Только коды: rejected values и тела ошибок не попадают в repair или диагностику.
            prompt = original + "\nREPAIR: Верни исправленный JSON. Ошибки: " + ",".join(codes)
        return PlannerResult(clarify(context.version), 2, tuple(codes))
