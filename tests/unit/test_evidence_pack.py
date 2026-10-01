import asyncio
from uuid import uuid4

from app.domain.evidence import CandidateEvidence
from app.services.evidence_pack import (
    TokenizerJsonCounter,
    build_evidence_pack,
    render_evidence_items,
)
from app.services.rerank import (
    RankedCandidate,
    lexical_scores,
    rank_candidates_bm25,
    rerank_candidates,
)


def _candidate(text: str, *, external_id: str = "W1", section: str = "abstract"):
    return CandidateEvidence(
        document_id=uuid4(), revision_id=uuid4(), chunk_id=uuid4(),
        source="openalex", external_id=external_id,
        canonical_url=f"https://openalex.org/{external_id}", title="Cellulose membrane",
        kind="article", publication_date=None, section=section, language="ru",
        text=text, channels=("qdrant",), score=0.7,
    )


def test_bm25_prefers_relevant_document():
    scores = lexical_scores("porous ceramic membrane", [
        "porous ceramic membrane separates liquids", "sodium ion cathode binder"
    ])
    assert scores[0] > scores[1]
    candidates = [_candidate("unrelated passage", external_id="B"),
                  _candidate("porous ceramic membrane passage", external_id="A")]
    ranked = rank_candidates_bm25("porous ceramic membrane", candidates, limit=2)
    assert ranked[0].candidate.external_id == "A"

def test_rerank_uses_selected_cross_encoder_scores_and_stable_tie_break():
    a = _candidate("irrelevant", external_id="B")
    b = _candidate("irrelevant", external_id="A")

    async def score(_query: str, _documents: list[str]) -> list[float]:
        return [0.9, 0.9]

    result = asyncio.run(rerank_candidates(
        "question", [a, b], score_documents=score, limit=2
    ))
    assert [item.candidate.external_id for item in result] == ["A", "B"]


def test_pack_keeps_exact_unicode_chunk_offsets_and_enforces_full_prompt_budget():
    text = "Не релевантный текст. Пористое керамическое покрытие удерживает частицы. Дальше."
    candidate = _candidate(text)
    ranked = [RankedCandidate(candidate, 0.8)]
    pack = build_evidence_pack(
        ranked, query="керамическое покрытие частицы",
        token_counter=lambda value: len(value.split()),
        prompt_prefix="idea context", prompt_suffix="output schema", token_budget=100,
    )
    assert 0 < pack.token_count <= pack.token_budget
    assert len(pack.items) == 1
    item = pack.items[0]
    assert text[item.span_start:item.span_end] == item.quoted_span
    assert item.revision_id == candidate.revision_id
    assert item.chunk_id == candidate.chunk_id
    assert item.evidence_id
    rendered = render_evidence_items(pack.items)
    assert pack.token_count == len(("idea context" + rendered + "output schema").split())


def test_pack_rejects_limit_overflow_and_avoids_injected_html_execution():
    candidate = _candidate("<script>alert(1)</script> unrelated source text")
    pack = build_evidence_pack(
        [RankedCandidate(candidate, 0.1)], query="unrelated source",
        token_counter=lambda value: len(value.split()), token_budget=20,
    )
    assert pack.items[0].quoted_span == "<script>alert(1)</script> unrelated source text"
    assert not hasattr(pack.items[0], "html")


def test_pack_skips_candidate_when_complete_metadata_cannot_fit():
    candidate = _candidate("porous ceramic membrane retains particles")
    pack = build_evidence_pack(
        [RankedCandidate(candidate, 0.1)], query="ceramic membrane",
        token_counter=lambda value: len(value.split()), token_budget=5,
    )
    assert pack.items == ()
    assert pack.token_count <= pack.token_budget


def test_gemma_token_counter_uses_special_tokens_and_reports_exact_id_count():
    class Encoding:
        ids = [2, 37, 81, 106]

    class TokenizerStub:
        add_special_tokens: bool | None = None

        def encode(self, _text: str, *, add_special_tokens: bool) -> Encoding:
            self.add_special_tokens = add_special_tokens
            return Encoding()

    tokenizer = TokenizerStub()
    counter = TokenizerJsonCounter(tokenizer)
    assert counter("prompt + serialized evidence") == 4
    assert tokenizer.add_special_tokens is True
