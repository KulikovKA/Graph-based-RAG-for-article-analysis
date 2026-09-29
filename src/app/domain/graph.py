"""Типизированная онтология публичного графа и DTO для извлечения."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class GraphNodeLabel(StrEnum):
    PATENT = "Patent"
    SCIENTIFIC_WORK = "ScientificWork"
    TECHNICAL_FEATURE = "TechnicalFeature"
    TECHNOLOGY = "Technology"
    CLASSIFICATION = "Classification"
    APPLICANT = "Applicant"
    INVENTOR = "Inventor"
    AUTHOR = "Author"


class GraphEdgeType(StrEnum):
    DISCLOSES_FEATURE = "DISCLOSES_FEATURE"
    USES_TECHNOLOGY = "USES_TECHNOLOGY"
    CLASSIFIED_AS = "CLASSIFIED_AS"
    CITES = "CITES"
    APPLIED_BY = "APPLIED_BY"
    INVENTED_BY = "INVENTED_BY"
    AUTHORED_BY = "AUTHORED_BY"
    RELATED_TO = "RELATED_TO"


EDGE_ENDPOINTS: dict[GraphEdgeType, tuple[frozenset[GraphNodeLabel], frozenset[GraphNodeLabel]]] = {
    GraphEdgeType.DISCLOSES_FEATURE: (
        frozenset({GraphNodeLabel.PATENT, GraphNodeLabel.SCIENTIFIC_WORK}),
        frozenset({GraphNodeLabel.TECHNICAL_FEATURE}),
    ),
    GraphEdgeType.USES_TECHNOLOGY: (
        frozenset(
            {
                GraphNodeLabel.PATENT,
                GraphNodeLabel.SCIENTIFIC_WORK,
                GraphNodeLabel.TECHNICAL_FEATURE,
            }
        ),
        frozenset({GraphNodeLabel.TECHNOLOGY}),
    ),
    GraphEdgeType.CLASSIFIED_AS: (
        frozenset({GraphNodeLabel.PATENT}),
        frozenset({GraphNodeLabel.CLASSIFICATION}),
    ),
    GraphEdgeType.CITES: (
        frozenset({GraphNodeLabel.PATENT, GraphNodeLabel.SCIENTIFIC_WORK}),
        frozenset({GraphNodeLabel.PATENT, GraphNodeLabel.SCIENTIFIC_WORK}),
    ),
    GraphEdgeType.APPLIED_BY: (
        frozenset({GraphNodeLabel.PATENT}),
        frozenset({GraphNodeLabel.APPLICANT}),
    ),
    GraphEdgeType.INVENTED_BY: (
        frozenset({GraphNodeLabel.PATENT}),
        frozenset({GraphNodeLabel.INVENTOR}),
    ),
    GraphEdgeType.AUTHORED_BY: (
        frozenset({GraphNodeLabel.SCIENTIFIC_WORK}),
        frozenset({GraphNodeLabel.AUTHOR}),
    ),
    GraphEdgeType.RELATED_TO: (
        frozenset({GraphNodeLabel.TECHNICAL_FEATURE}),
        frozenset({GraphNodeLabel.TECHNICAL_FEATURE}),
    ),
}


class GraphCandidateV1(BaseModel):
    """Непроверенный ответ экстрактора; graph_index проверяет онтологию и provenance."""

    model_config = ConfigDict(extra="forbid")

    edge_type: str
    target_label: str
    target_text: str = Field(min_length=1, max_length=160)
    evidence_chunk_id: str
    span_start: int = Field(ge=0)
    span_end: int = Field(ge=1)
    quote: str = Field(min_length=1, max_length=512)
    confidence: float = Field(ge=0, le=1)


GRAPH_EXTRACTION_SCHEMA_V1: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "facts": {
            "type": "array",
            "maxItems": 32,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "edge_type": {"type": "string", "enum": [item.value for item in GraphEdgeType]},
                    "target_label": {
                        "type": "string",
                        "enum": [item.value for item in GraphNodeLabel],
                    },
                    "target_text": {"type": "string", "minLength": 1, "maxLength": 160},
                    "evidence_chunk_id": {"type": "string"},
                    "span_start": {"type": "integer", "minimum": 0},
                    "span_end": {"type": "integer", "minimum": 1},
                    "quote": {"type": "string", "minLength": 1, "maxLength": 512},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": [
                    "edge_type",
                    "target_label",
                    "target_text",
                    "evidence_chunk_id",
                    "span_start",
                    "span_end",
                    "quote",
                    "confidence",
                ],
            },
        },
    },
    "required": ["facts"],
}
