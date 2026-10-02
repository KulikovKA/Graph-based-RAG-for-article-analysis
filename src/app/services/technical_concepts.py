"""Versioned, source-grounded semantic concept mention contract."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ConceptType = Literal[
    "MATERIAL",
    "DEVICE",
    "PROPERTY",
    "PERFORMANCE",
    "ANALYTE",
    "PROCESS",
    "MECHANISM",
    "OPERATING_CONDITION",
    "MORPHOLOGY",
    "TECHNOLOGY",
    "APPLICATION",
    "OTHER",
]
CONCEPT_SCHEMA_VERSION = "technical-concept-mention-v1"
_SPACE = re.compile(r"\s+")
_PUNCT = re.compile(r"[\W_]+", re.UNICODE)


class TechnicalConceptMentionV1(BaseModel):
    """One semantic mention anchored to one EvidenceChunk using Python codepoint offsets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    concept_type: ConceptType
    canonical_name: str = Field(min_length=1, max_length=256)
    surface_text: str = Field(min_length=1, max_length=512)
    quote: str = Field(min_length=1, max_length=1200)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
    qualifiers: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("canonical_name", "surface_text", "quote")
    @classmethod
    def trim_nonempty(cls, value: str) -> str:
        if value != value.strip() or not value:
            raise ValueError("text fields must be non-empty and trimmed")
        return value

    @model_validator(mode="after")
    def valid_span(self) -> TechnicalConceptMentionV1:
        if self.end_offset <= self.start_offset:
            raise ValueError("end_offset must be greater than start_offset")
        if self.surface_text not in self.quote:
            raise ValueError("surface_text must occur within quote")
        return self


def normalize_concept_name(value: str) -> str:
    """Conservative identity normalization; intentionally does not stem or singularize."""
    value = unicodedata.normalize("NFKC", value).casefold()
    value = _SPACE.sub(" ", value).strip()
    return _SPACE.sub(" ", _PUNCT.sub(" ", value)).strip()


def validate_grounding(mention: TechnicalConceptMentionV1, chunk_text: str) -> None:
    """Validate exact Unicode-codepoint slice and quote against immutable chunk text."""
    if not chunk_text or mention.end_offset > len(chunk_text):
        raise ValueError("mention offsets are outside the evidence chunk")
    if chunk_text[mention.start_offset : mention.end_offset] != mention.surface_text:
        raise ValueError("mention offsets do not resolve to surface_text")
    if mention.quote not in chunk_text:
        raise ValueError("quote does not occur in the evidence chunk")
    quote_start = chunk_text.find(mention.quote)
    grounded = False
    while quote_start >= 0:
        surface_start = mention.quote.find(mention.surface_text)
        while surface_start >= 0:
            if quote_start + surface_start == mention.start_offset:
                grounded = True
                break
            surface_start = mention.quote.find(mention.surface_text, surface_start + 1)
        if grounded:
            break
        quote_start = chunk_text.find(mention.quote, quote_start + 1)
    if not grounded:
        raise ValueError("surface offsets do not point inside the quoted occurrence")


def validate_or_reanchor_draft(
    draft: dict[str, Any], chunk_text: str
) -> TechnicalConceptMentionV1:
    """Accept only exact source spans, repairing whitespace and uniquely recoverable offsets."""
    value = dict(draft)
    for field in ("canonical_name", "surface_text", "quote"):
        if isinstance(value.get(field), str):
            value[field] = value[field].strip()
    quote = value.get("quote")
    surface = value.get("surface_text")
    if not isinstance(quote, str) or not isinstance(surface, str) or not quote or not surface:
        raise ValueError("quote and surface_text are required")
    starts: set[int] = set()
    quote_at = chunk_text.find(quote)
    while quote_at >= 0:
        surface_at = quote.find(surface)
        while surface_at >= 0:
            starts.add(quote_at + surface_at)
            surface_at = quote.find(surface, surface_at + 1)
        quote_at = chunk_text.find(quote, quote_at + 1)
    if not starts:
        raise ValueError("no exact source occurrence for surface within quote")
    preferred = value.get("start_offset")
    if preferred not in starts:
        if len(starts) != 1:
            raise ValueError("surface occurrence is ambiguous")
        preferred = next(iter(starts))
    value["start_offset"] = preferred
    value["end_offset"] = preferred + len(surface)
    mention = TechnicalConceptMentionV1.model_validate(value)
    validate_grounding(mention, chunk_text)
    return mention


def concept_identity(mention: TechnicalConceptMentionV1) -> tuple[str, str]:
    """Type plus normalized concept name; qualifiers remain mention scope."""
    return mention.concept_type, normalize_concept_name(mention.canonical_name)
