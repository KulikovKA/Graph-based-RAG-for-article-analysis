from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.services.technical_concepts import (
    TechnicalConceptMentionV1,
    concept_identity,
    normalize_concept_name,
    validate_grounding,
    validate_or_reanchor_draft,
)


def mention(**overrides: object) -> TechnicalConceptMentionV1:
    value: dict[str, object] = {
        "concept_type": "MATERIAL",
        "canonical_name": "graphene",
        "surface_text": "graphene",
        "quote": "α graphene sensor",
        "start_offset": 2,
        "end_offset": 10,
        "qualifiers": {},
    }
    value.update(overrides)
    return TechnicalConceptMentionV1.model_validate(value)


def test_valid_type_and_exact_unicode_codepoint_grounding() -> None:
    item = mention()
    validate_grounding(item, "α graphene sensor")
    assert item.start_offset == 2


def test_rejects_surface_not_inside_quote() -> None:
    with pytest.raises(ValidationError):
        mention(quote="α sheet sensor")


@pytest.mark.parametrize("changes", [{"start_offset": 1}, {"end_offset": 99}])
def test_rejects_invalid_offsets(changes: dict[str, object]) -> None:
    item = mention(**changes)
    with pytest.raises(ValueError):
        validate_grounding(item, "α graphene sensor")


def test_rejects_quote_outside_source() -> None:
    with pytest.raises(ValueError):
        validate_grounding(
            mention(quote="graphene sensor!", start_offset=2, end_offset=10), "α graphene sensor"
        )


def test_rejects_invalid_type_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        mention(concept_type="NOT_A_TYPE")
    with pytest.raises(ValidationError):
        mention(unreviewed=True)


def test_normalization_is_nfkc_casefold_and_punctuation_safe() -> None:
    assert normalize_concept_name("  Room‑Temperature  ") == "room temperature"
    assert normalize_concept_name("NH₃") == normalize_concept_name("nh3")
    assert normalize_concept_name("nanowires") != normalize_concept_name("nanowire")


def test_scope_qualifiers_do_not_erase_critical_identity() -> None:
    no2 = mention(
        concept_type="ANALYTE",
        canonical_name="NO2",
        surface_text="NO2",
        quote="NO2 sensing",
        start_offset=0,
        end_offset=3,
    )
    nh3 = mention(
        concept_type="ANALYTE",
        canonical_name="NH3",
        surface_text="NH3",
        quote="NH3 sensing",
        start_offset=0,
        end_offset=3,
    )
    assert concept_identity(no2) != concept_identity(nh3)


def test_property_qualifier_is_preserved_on_mention() -> None:
    high = mention(
        concept_type="PROPERTY",
        canonical_name="selectivity",
        surface_text="selectivity",
        quote="high selectivity",
        start_offset=5,
        end_offset=16,
        qualifiers={"degree": "high", "analyte": "NO2"},
    )
    low = mention(
        concept_type="PROPERTY",
        canonical_name="selectivity",
        surface_text="selectivity",
        quote="low selectivity",
        start_offset=4,
        end_offset=15,
        qualifiers={"degree": "low", "analyte": "NH3"},
    )
    assert concept_identity(high) == concept_identity(low)
    assert high.qualifiers != low.qualifiers


def test_reanchors_trimmed_surface_to_unique_exact_source_occurrence() -> None:
    item = validate_or_reanchor_draft(
        {
            "concept_type": "ANALYTE",
            "canonical_name": " NO2 ",
            "surface_text": " NO2 ",
            "quote": " NO2 sensing ",
            "start_offset": 0,
            "end_offset": 5,
            "qualifiers": {},
        },
        "Gas NO2 sensing",
    )
    assert item.surface_text == "NO2"
    assert (item.start_offset, item.end_offset) == (4, 7)


def test_rejects_ambiguous_reanchor_and_unverifiable_quote() -> None:
    draft = {
        "concept_type": "MATERIAL",
        "canonical_name": "graphene",
        "surface_text": "graphene",
        "quote": "graphene sensor",
        "start_offset": 8,
        "end_offset": 8,
        "qualifiers": {},
    }
    with pytest.raises(ValueError, match="ambiguous"):
        validate_or_reanchor_draft(draft, "graphene sensor; graphene sensor")
    with pytest.raises(ValueError, match="exact source"):
        validate_or_reanchor_draft(draft, "graphene device")
