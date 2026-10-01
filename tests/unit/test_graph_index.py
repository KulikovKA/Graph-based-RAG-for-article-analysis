from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.services.graph_index import (
    GraphChunk,
    GraphIndexingService,
    GraphRevision,
    enrich_graph_candidates,
)


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


def test_graph_quote_offsets_are_enriched_deterministically_with_unicode() -> None:
    revision = _revision("Before 📷, the heat pump transfers thermal energy.")
    chunk = revision.chunks[0]
    quote = "heat pump transfers thermal energy"
    result = enrich_graph_candidates(
        revision.chunks,
        [{"edge_type": "DISCLOSES_FEATURE", "target_text": "heat pump",
          "quote": quote, "confidence": 0.96}],
    )
    assert len(result) == 1
    candidate = result[0]
    start, end = candidate["span_start"], candidate["span_end"]
    assert isinstance(start, int) and isinstance(end, int)
    assert chunk.text[start:end] == quote
    assert candidate["evidence_chunk_id"] == str(chunk.id)
    assert candidate["target_label"] == "TechnicalFeature"


def test_graph_enrichment_rejects_duplicate_quote_provenance_and_invalid_semantics() -> None:
    revision = _revision("heat pump supports water. Later, heat pump supports water.")
    quote = "heat pump supports water"
    candidate = {"edge_type": "DISCLOSES_FEATURE", "target_text": "heat pump",
                 "quote": quote, "confidence": 0.96}
    assert enrich_graph_candidates(revision.chunks, [candidate]) == []
    assert enrich_graph_candidates(
        revision.chunks,
        [candidate | {"quote": "not in source"}, candidate | {"target_text": "unrelated"},
         candidate | {"edge_type": "INVENTED_RELATION"}],
    ) == []


def test_extractor_v2_accepts_semantic_draft_without_model_offsets() -> None:
    import asyncio

    from app.services.graph_index import InferenceGraphExtractor

    class Provider:
        async def complete_json(self, **kwargs):  # type: ignore[no-untyped-def]
            self.kwargs = kwargs
            return SimpleNamespace(
                value={
                    "facts": [
                        {
                            "edge_type": "DISCLOSES_FEATURE",
                            "target_text": "heat pump",
                            "quote": "heat pump transfers thermal energy",
                            "confidence": 0.95,
                        }
                    ]
                }
            )

    provider = Provider()
    chunks = (GraphChunk(uuid4(), "abstract", "Before 📷, heat pump transfers thermal energy."),)
    extractor = InferenceGraphExtractor(provider, model_id="fixture", model_revision="digest")
    result = asyncio.run(extractor.extract(chunks, request_id="test"))
    assert len(result) == 1
    assert result[0]["span_start"] == chunks[0].text.index("heat pump")
    assert result[0]["span_end"] == chunks[0].text.index("heat pump") + len(result[0]["quote"])
    properties = provider.kwargs["schema"]["properties"]["facts"]["items"]["properties"]
    assert "span_start" not in properties
    assert "span_start/span_end" not in provider.kwargs["prompt"]


def test_graph_extractor_splits_a_truncated_six_chunk_batch_and_recovers() -> None:
    import asyncio
    import json

    from app.domain.inference import InferenceOutputLimit
    from app.services.graph_index import InferenceGraphExtractor

    class Provider:
        def __init__(self) -> None:
            self.calls: list[tuple[int, str, int, int | None, float]] = []

        async def complete_json(self, **kwargs):  # type: ignore[no-untyped-def]
            chunks_json = kwargs["prompt"].split("Chunks JSON: ", 1)[1]
            chunk_count = len(json.loads(chunks_json))
            self.calls.append((
                chunk_count, kwargs["request_id"], kwargs["max_output_tokens"],
                kwargs["context_window"], kwargs["timeout"],
            ))
            if chunk_count == 6:
                raise InferenceOutputLimit(max_output_tokens=kwargs["max_output_tokens"])
            return SimpleNamespace(value={"facts": []})

    provider = Provider()
    chunks = tuple(
        GraphChunk(uuid4(), "abstract", f"Evidence text for chunk {index}.")
        for index in range(6)
    )
    extractor = InferenceGraphExtractor(
        provider, model_id="fixture", model_revision="digest", max_output_tokens=2048,
        context_window=16384, timeout=300,
    )

    result = asyncio.run(extractor.extract(chunks, request_id="split-run"))

    assert result == []
    assert [call[0] for call in provider.calls] == [6, 3, 3]
    assert len({call[1] for call in provider.calls}) == 3
    assert {call[2] for call in provider.calls} == {2048}
    assert {call[3] for call in provider.calls} == {16384}
    assert {call[4] for call in provider.calls} == {300}


def test_graph_extractor_single_chunk_truncation_is_a_controlled_failure() -> None:
    import asyncio
    import json

    import pytest

    from app.domain.inference import InferenceOutputLimit
    from app.services.graph_index import InferenceGraphExtractor

    class Provider:
        def __init__(self) -> None:
            self.batch_sizes: list[int] = []

        async def complete_json(self, **kwargs):  # type: ignore[no-untyped-def]
            chunks_json = kwargs["prompt"].split("Chunks JSON: ", 1)[1]
            self.batch_sizes.append(len(json.loads(chunks_json)))
            raise InferenceOutputLimit(max_output_tokens=kwargs["max_output_tokens"])

    provider = Provider()
    chunks = tuple(
        GraphChunk(uuid4(), "abstract", f"Evidence text for chunk {index}.")
        for index in range(6)
    )
    extractor = InferenceGraphExtractor(
        provider, model_id="fixture", model_revision="digest", max_output_tokens=2048,
        context_window=16384, timeout=300,
    )

    with pytest.raises(InferenceOutputLimit) as error:
        asyncio.run(extractor.extract(chunks, request_id="single-fail"))

    assert error.value.done_reason == "length"
    assert provider.batch_sizes == [6, 3, 1]


def test_graph_extractor_does_not_retry_other_protocol_errors() -> None:
    import asyncio

    import pytest

    from app.domain.inference import InferenceProtocolError
    from app.services.graph_index import InferenceGraphExtractor

    class Provider:
        calls = 0

        async def complete_json(self, **_kwargs):  # type: ignore[no-untyped-def]
            self.calls += 1
            raise InferenceProtocolError("invalid provider channel")

    provider = Provider()
    extractor = InferenceGraphExtractor(provider, model_id="fixture", model_revision="digest")

    with pytest.raises(InferenceProtocolError, match="invalid provider channel"):
        asyncio.run(
            extractor.extract(
                (GraphChunk(uuid4(), "abstract", "One evidence chunk."),),
                request_id="protocol-fail",
            )
        )

    assert provider.calls == 1


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
