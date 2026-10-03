from __future__ import annotations

import csv
from pathlib import Path

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


@pytest.mark.parametrize("canonical", ["NO2", "NH3"])
@pytest.mark.parametrize("surface", ["gas", "gases", "liquids"])
def test_generic_grounded_surface_cannot_assert_specific_canonical_identity(
    canonical: str, surface: str
) -> None:
    draft = mention(
        concept_type="ANALYTE",
        canonical_name=canonical,
        surface_text=surface,
        quote=surface,
        start_offset=0,
        end_offset=len(surface),
    )
    with pytest.raises(ValueError, match="canonical"):
        validate_grounding(draft, surface)
    with pytest.raises(ValueError, match="canonical"):
        validate_or_reanchor_draft(draft.model_dump(), surface)


def test_canonical_elsewhere_in_chunk_does_not_ground_generic_surface() -> None:
    draft = mention(
        concept_type="ANALYTE",
        canonical_name="NO2",
        surface_text="gas",
        quote="gas sensing",
        start_offset=0,
        end_offset=3,
    )
    with pytest.raises(ValueError, match="canonical"):
        validate_grounding(draft, "gas sensing; NO2 was not measured")


@pytest.mark.parametrize("surface,canonical", [("NH₃", "NH3"), ("ＮＯ２", "no2")])
def test_equivalent_unicode_identity_keeps_original_source_offsets(
    surface: str, canonical: str
) -> None:
    source = "🧪 е\u0301 " + surface + " sensing"
    start = source.index(surface)
    draft = mention(
        concept_type="ANALYTE",
        canonical_name=canonical,
        surface_text=surface,
        quote=surface + " sensing",
        start_offset=start,
        end_offset=start + len(surface),
    )
    validate_grounding(draft, source)
    assert validate_or_reanchor_draft(draft.model_dump(), source) == draft
    with pytest.raises(ValueError, match="offsets"):
        validate_grounding(draft.model_copy(update={"start_offset": start + 1}), source)


def test_normalized_surface_is_not_substituted_for_exact_unicode_source() -> None:
    draft = mention(
        concept_type="ANALYTE",
        canonical_name="NH3",
        surface_text="NH3",
        quote="NH3 sensing",
        start_offset=0,
        end_offset=3,
    )
    with pytest.raises(ValueError):
        validate_or_reanchor_draft(draft.model_dump(), "NH₃ sensing")


def test_quote_must_cover_selected_occurrence_of_repeated_surface() -> None:
    draft = mention(quote="graphene sensor", start_offset=17, end_offset=25)
    with pytest.raises(ValueError, match="quoted occurrence"):
        validate_grounding(draft, "graphene sensor; graphene device")


def test_all_eight_audited_quote_surface_pairs_reject_unsupported_identity() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "docs/analysis/HYBRID_ZERO_AUDIT/accepted_semantic_findings.csv"
    )
    with path.open(encoding="utf-8", newline="") as stream:
        findings = list(csv.DictReader(stream))
    assert len(findings) == 8
    for finding in findings:
        # Публичный excerpt служит минимальным тестовым chunk, не исходным полным текстом.
        source = finding["quote"]
        surface = finding["surface_text"]
        start = source.index(surface)
        item = mention(
            concept_type=finding["concept_type"],
            canonical_name=finding["canonical_name"],
            surface_text=surface,
            quote=source,
            start_offset=start,
            end_offset=start + len(surface),
        )
        with pytest.raises(ValueError, match="canonical"):
            validate_or_reanchor_draft(item.model_dump(), source)
