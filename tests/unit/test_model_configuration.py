"""Модельные digests и dimension не расходятся между runtime config и inventory."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_pinned_models_match_inventory() -> None:
    config = yaml.safe_load((ROOT / "config/models.yaml").read_text(encoding="utf-8"))
    inventory = json.loads((ROOT / "docs/model_inventory.json").read_text(encoding="utf-8"))
    for role in ("planner", "analyst"):
        actual = inventory["models"][role]
        selected = config["generation"][role]
        assert actual["id"] == selected["model_id"]
        assert actual["digest"] == selected["digest"]
    embedding = inventory["models"]["embedding"]
    assert embedding["id"] == config["embedding"]["model_id"]
    assert embedding["digest"] == config["embedding"]["digest"]
    assert embedding["measured_dimension"] == config["embedding"]["dimension"]
    reranker = inventory["models"]["reranker"]
    assert reranker["repository"] == config["reranker"]["model_id"]
    assert reranker["revision"] == config["reranker"]["revision"]
