"""Строгий необязательный judge без доступа к production request path."""

from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Scores(BaseModel):
    model_config = ConfigDict(extra="forbid")
    faithfulness: int = Field(strict=True, ge=0, le=4)
    relevance: int = Field(strict=True, ge=0, le=4)
    completeness: int = Field(strict=True, ge=0, le=4)
    feature_matching: int = Field(strict=True, ge=0, le=4)
    conclusion_validity: int = Field(strict=True, ge=0, le=4)


class ProblemSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    start: int = Field(strict=True, ge=0)
    end: int = Field(strict=True, gt=0)


class JudgeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    scores: Scores
    cited_problem_spans: list[ProblemSpan] = Field(max_length=64)
    rationale: Literal["SUPPORTED", "UNSUPPORTED_RELATION", "INCOMPLETE", "IRRELEVANT", "UNCERTAIN"]
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)


def file_judge(value: object) -> Callable[[dict[str, Any], bool], object]:
    def invoke(_observation: dict[str, Any], _retry: bool) -> object:
        return value

    return invoke


def judge_case(
    case_id: str,
    observation: dict[str, Any],
    invoke: Callable[[dict[str, Any], bool], object] | None = None,
) -> tuple[JudgeResult | None, str]:
    """Один schema retry; наружу не возвращаются rejected values/exception bodies."""
    if invoke is None:
        return None, "DISABLED"
    for retry in (False, True):
        try:
            result = JudgeResult.model_validate(invoke(observation, retry))
            if result.case_id != case_id:
                continue
            evidence = {item["evidence_id"]: item for item in observation["evidence"]}
            if any(
                span.evidence_id not in evidence
                or span.end <= span.start
                or span.start < evidence[span.evidence_id]["span_start"]
                or span.end > evidence[span.evidence_id]["span_end"]
                for span in result.cited_problem_spans
            ):
                continue
            return result, "OK"
        except (ValidationError, ValueError, TypeError, KeyError):
            continue
        except Exception:
            return None, "UNAVAILABLE"
    return None, "INVALID_RESULT"
