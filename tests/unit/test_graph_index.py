from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.services.graph_index import GraphChunk, GraphIndexingService, GraphRevision


def _service() -> GraphIndexingService:
    service = object.__new__(GraphIndexingService)
    service.graph = SimpleNamespace(namespace="graph-unit-test")
    service.extractor_version = "extractor-test-v1"
    service.vocabulary_version = "feature-test-v1"
    return service


def _revision(text: str = "The heat pump transfers thermal energy.") -> GraphRevision:
    revision_id = uuid4()
    return GraphRevision(
        id=revision_id,
        document_id=uuid4(),
        retrieved_at=datetime.now(UTC),
        normalized_json={"source": "openalex"},
        chunks=(GraphChunk(uuid4(), "abstract", text),),
    )


def _candidate(
    chunk: GraphChunk, *, start: int, end: int, **overrides: object
) -> dict[str, object]:
    text = chunk.text[start:end]
    return {
        "edge_type": "DISCLOSES_FEATURE",
        "target_label": "TechnicalFeature",
        "target_text": "heat pump",
        "evidence_chunk_id": str(chunk.id),
        "span_start": start,
        "span_end": end,
        "quote": text,
        "confidence": 0.96,
        **overrides,
    }


def test_graph_facts_require_enum_edge_and_matching_chunk_span() -> None:
    revision = _revision()
    chunk = revision.chunks[0]
    start, end = chunk.text.index("heat pump"), chunk.text.index("heat pump") + len("heat pump")
    service = _service()

    facts = service._validated_facts(
        revision,
        [
            _candidate(chunk, start=start, end=end),
            _candidate(chunk, start=start, end=end, edge_type="DISCUSSES"),
            _candidate(chunk, start=start, end=end, target_label="IdeaFeature"),
            _candidate(chunk, start=start, end=end, evidence_chunk_id=str(uuid4())),
            _candidate(chunk, start=start, end=end, quote="made up evidence"),
            _candidate(chunk, start=start, end=end, confidence=0.4),
            _candidate(chunk, start=start, end=end, target_text="invented mechanism"),
        ],
    )

    assert len(facts) == 1
    fact = facts[0]
    assert fact.edge_type == "DISCLOSES_FEATURE"
    assert fact.chunk_id == chunk.id
    assert fact.span_start == start
    assert fact.span_end == end
    assert fact.provenance_key == f"chunk:{chunk.id}:{start}:{end}"
    assert fact.confidence == 0.96
    assert fact.validated_at is not None


def test_same_text_in_different_revisions_gets_distinct_provenance_keys() -> None:
    first = _revision()
    second = GraphRevision(
        id=uuid4(),
        document_id=first.document_id,
        retrieved_at=first.retrieved_at,
        normalized_json=first.normalized_json,
        chunks=(GraphChunk(uuid4(), first.chunks[0].section, first.chunks[0].text),),
    )
    start = first.chunks[0].text.index("heat pump")
    end = start + len("heat pump")
    service = _service()

    first_fact = service._validated_facts(
        first, [_candidate(first.chunks[0], start=start, end=end)]
    )[0]
    second_fact = service._validated_facts(
        second, [_candidate(second.chunks[0], start=start, end=end)]
    )[0]

    assert first_fact.from_key != second_fact.from_key
    assert first_fact.chunk_id != second_fact.chunk_id
    assert first_fact.logical_key_hash != second_fact.logical_key_hash
