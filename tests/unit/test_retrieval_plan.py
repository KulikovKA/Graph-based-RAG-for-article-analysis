from uuid import uuid4

from app.domain.evidence import CandidateEvidence
from app.domain.planner import FeatureV1, IdeaV1
from app.services.retrieval import build_retrieval_query, reciprocal_rank_fusion


def _idea(features: int = 0) -> IdeaV1:
    return IdeaV1(
        domain="thermal systems",
        features=[FeatureV1(id=uuid4(), text=f"feature {index}") for index in range(features)],
        technologies=["heat pump"],
        constraints=["low temperature"],
        language="en",
    )


def _candidate(*, chunk: str, url: str, source: str = "openalex", score: float = 1.0):
    return CandidateEvidence(
        document_id=uuid4(),
        revision_id=uuid4(),
        chunk_id=uuid4(),
        source=source,
        external_id=chunk,
        canonical_url=url,
        title=chunk,
        kind="article",
        publication_date=None,
        section="abstract",
        language="en",
        text="supporting source text",
        channels=(source,),
        score=score,
    )


def test_query_plan_keeps_original_and_caps_feature_subqueries() -> None:
    query = build_retrieval_query("  original   question ", _idea(20), max_features=3)
    assert query.original_query == "  original   question "
    assert query.subqueries[0].text == "original question"
    assert len(query.subqueries) == 4
    assert all(len(item.text) <= 512 for item in query.subqueries)
    assert sum(item.feature_id is not None for item in query.subqueries) == 3


def test_empty_decomposition_falls_back_to_the_original_query() -> None:
    query = build_retrieval_query("saved source question", _idea())
    assert [item.text for item in query.subqueries] == ["saved source question"]
    assert query.original_query == "saved source question"


def test_fusion_is_stable_and_deduplicates_canonical_sources() -> None:
    first = _candidate(chunk="W1", url="https://example.org/Work/")
    duplicate = _candidate(chunk="W1-copy", url="https://example.org/Work")
    second = _candidate(chunk="W2", url="https://example.org/other", score=0.8)

    output = reciprocal_rank_fusion([[first, second], [duplicate, second]], limit=10)

    assert [item.canonical_url.rstrip("/") for item in output] == [
        "https://example.org/Work",
        "https://example.org/other",
    ]
    assert output[0].channels == ("openalex",)
    assert reciprocal_rank_fusion([[first, second], [duplicate, second]], limit=10) == output
