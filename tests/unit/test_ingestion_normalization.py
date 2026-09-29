"""Проверки детерминированной нормализации без зависимости от PostgreSQL."""

import hashlib

import pytest

from app.domain.documents import DocumentSection
from app.services.ingestion import canonical_external_id, chunk_sections


def test_source_ids_are_canonical_and_validated() -> None:
    assert canonical_external_id("epo_ops", "EP.1234567.A1") == "EP1234567A1"
    assert canonical_external_id("openalex", "https://openalex.org/w123") == "W123"
    with pytest.raises(ValueError):
        canonical_external_id("openalex", "not-a-work")


def test_section_chunk_offsets_hashes_and_language_survive_unicode() -> None:
    source = "Первое предложение. Второе предложение. " + "длинный текст " * 20
    chunks = chunk_sections((DocumentSection("abstract", source, "ru"),), chunk_size=100)
    assert len(chunks) > 1
    assert all(item["language"] == "ru" for item in chunks)
    assert all(
        item["text"] == source[item["section_start"] : item["section_end"]]
        for item in chunks
    )
    assert all(
        item["hash"] == hashlib.sha256(item["text"].encode("utf-8")).hexdigest()
        for item in chunks
    )
    assert [item["ordinal"] for item in chunks] == list(range(len(chunks)))


def test_sections_are_chunked_independently() -> None:
    chunks = chunk_sections(
        (DocumentSection("abstract", "Summary."), DocumentSection("claims", "Claim one.")),
        chunk_size=100,
    )
    assert [(item["section"], item["ordinal"]) for item in chunks] == [
        ("abstract", 0),
        ("claims", 0),
    ]
