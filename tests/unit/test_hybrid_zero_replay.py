from __future__ import annotations

import pytest
from scripts.hybrid_zero_replay import _assert_conservation, _classification


def test_synthetic_empty_and_all_rejected_classification() -> None:
    assert _classification([{"status": "MODEL_EMPTY", "candidate_count": 0}], 0) == "MODEL_EMPTY"
    assert (
        _classification(
            [
                {
                    "status": "success",
                    "candidate_count": 2,
                    "accepted_candidate_count": 0,
                    "rejected_candidate_count": 2,
                }
            ],
            0,
        )
        == "ALL_REJECTED"
    )


def test_synthetic_partial_and_mixed_chunk_classification() -> None:
    partial = [
        {
            "status": "success",
            "candidate_count": 3,
            "accepted_candidate_count": 1,
            "rejected_candidate_count": 2,
        }
    ]
    assert _classification(partial, 0) == "PARTIAL_ACCEPTED"
    mixed = [
        {
            "status": "success",
            "candidate_count": 1,
            "accepted_candidate_count": 1,
            "rejected_candidate_count": 0,
        },
        {
            "status": "MODEL_EMPTY",
            "candidate_count": 0,
            "accepted_candidate_count": 0,
            "rejected_candidate_count": 0,
        },
    ]
    assert _classification(mixed, 0) == "MIXED_CHUNKS"


def test_synthetic_retry_recovered_and_inference_failure() -> None:
    assert (
        _classification(
            [
                {
                    "status": "success",
                    "candidate_count": 1,
                    "accepted_candidate_count": 1,
                    "rejected_candidate_count": 0,
                }
            ],
            1,
        )
        == "RETRY_RECOVERED"
    )
    assert _classification([{"status": "TIMEOUT"}], 0) == "INFERENCE_FAILURE"


def test_candidate_count_conservation_fixture() -> None:
    _assert_conservation(
        [
            {
                "chunks": [
                    {
                        "candidate_count": 4,
                        "accepted_candidate_count": 1,
                        "rejected_candidate_count": 3,
                    }
                ]
            }
        ]
    )
    with pytest.raises(RuntimeError, match="candidate count conservation"):
        _assert_conservation(
            [
                {
                    "chunks": [
                        {
                            "candidate_count": 4,
                            "accepted_candidate_count": 1,
                            "rejected_candidate_count": 2,
                        }
                    ]
                }
            ]
        )


def test_incomplete_attempt_counts_remain_unknown() -> None:
    _assert_conservation(
        [
            {
                "chunks": [
                    {
                        "candidate_count": None,
                        "accepted_candidate_count": 0,
                        "rejected_candidate_count": None,
                    }
                ]
            }
        ]
    )
