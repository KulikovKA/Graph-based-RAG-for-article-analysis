"""Disposable ARCH-001 donor probe; no application code or real model calls."""
import asyncio
import hashlib
import json
import os
import platform
import tempfile
import uuid
from importlib.metadata import version
from pathlib import Path

import numpy as np
from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc, Tokenizer, compute_mdhash_id
from qdrant_client import QdrantClient


class CharacterTokenizer:
    def encode(self, text):
        return list(map(ord, text))

    def decode(self, tokens):
        return "".join(map(chr, tokens))


async def embed(texts):
    # Constant vectors deliberately test plumbing, never retrieval relevance.
    return np.tile(np.array([1, 0, 0, 0], dtype=np.float32), (len(texts), 1))


llm_calls = 0


async def forbidden_llm(*args, **kwargs):
    global llm_calls
    llm_calls += 1
    raise AssertionError("Smoke must not invoke a language model")


def fixture():
    return {
        "chunks": [{"content": "Sensor measures temperature using a thermal probe.",
                    "source_id": "evidence-A", "chunk_order_index": 7,
                    "file_path": "fixture://patent-A/revision-1/chunk-7"}],
        "entities": [
            {"entity_name": name, "entity_type": "COMPONENT", "description": name,
             "source_id": "evidence-A", "file_path": "fixture://patent-A/revision-1/chunk-7"}
            for name in ["Sensor", "ThermalProbe"]],
        "relationships": [{"src_id": "Sensor", "tgt_id": "ThermalProbe",
                           "description": "Sensor uses ThermalProbe", "keywords": "measurement",
                           "weight": 1, "source_id": "evidence-A",
                           "file_path": "fixture://patent-A/revision-1/chunk-7"}],
    }


async def main():
    assert not os.getenv("NEO4J_WORKSPACE") and not os.getenv("QDRANT_WORKSPACE"), "Global workspace override invalidates isolation probe"
    run_id = uuid.uuid4().hex[:10]
    root = tempfile.mkdtemp(prefix="arch001-")

    def make_rag(suffix):
        return LightRAG(
            working_dir=root, workspace=f"arch001_{run_id}_{suffix}",
            graph_storage="Neo4JStorage", vector_storage="QdrantVectorDBStorage",
            llm_model_func=forbidden_llm,
            embedding_func=EmbeddingFunc(embedding_dim=4, max_token_size=8192,
                                         model_name="arch001-fixture", func=embed),
            tokenizer=Tokenizer("arch001-character", CharacterTokenizer()),
            vector_db_storage_cls_kwargs={"cosine_better_than_threshold": 0.1},
        )

    rag, empty = make_rag("a"), make_rag("b")
    report = {"python": platform.python_version(), "lightrag": version("lightrag-hku"),
              "neo4j_driver": version("neo4j"), "qdrant_client": version("qdrant-client"),
              "run_id": run_id, "checks": {}, "limitations_observed": {}}
    try:
        await rag.initialize_storages()
        await empty.initialize_storages()
        kg = fixture()
        original = json.dumps(kg, sort_keys=True)
        await rag.ainsert_custom_kg(kg, full_doc_id="document-A-revision-1")
        assert json.dumps(kg, sort_keys=True) == original
        report["checks"]["custom_kg_insert_input_unchanged"] = True
        chunk_id = compute_mdhash_id(kg["chunks"][0]["content"], prefix="chunk-")
        node = await rag.chunk_entity_relation_graph.get_node("Sensor")
        edge = await rag.chunk_entity_relation_graph.get_edge("Sensor", "ThermalProbe")
        chunk = await rag.text_chunks.get_by_id(chunk_id)
        assert node["source_id"] == edge["source_id"] == chunk_id
        assert chunk["full_doc_id"] == "document-A-revision-1" and chunk["chunk_order_index"] == 7
        report["checks"]["source_alias_to_chunk_to_document"] = True
        param = QueryParam(mode="mix", only_need_context=True, enable_rerank=False,
                           hl_keywords=["measurement"], ll_keywords=["Sensor"],
                           top_k=10, chunk_top_k=10, max_total_tokens=20000)
        context = await rag.aquery("How does the Sensor measure temperature?", param=param)
        data = await rag.aquery_data("How does the Sensor measure temperature?", param=param)
        Path("/tmp/arch001-query.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        assert data["status"] == "success", data
        assert kg["chunks"][0]["content"] in context
        assert any(c["chunk_id"] == chunk_id for c in data["data"]["chunks"])
        assert any(r["file_path"] == "chunk-7" for r in data["data"]["references"])
        report["limitations_observed"]["file_path_normalized_to_basename"] = True
        report["checks"]["context_and_structured_references"] = True
        report["retrieval"] = data
        report["context_sha256"] = hashlib.sha256(context.encode()).hexdigest()
        client = QdrantClient(url=os.environ["QDRANT_URL"])
        def counts():
            return {c.name: client.count(c.name, exact=True).count
                    for c in client.get_collections().collections}
        before = counts()
        await rag.ainsert_custom_kg(kg, full_doc_id="document-A-revision-1")
        after = counts()
        assert before == after
        report["checks"]["repeat_insert_vector_counts_stable"] = True
        report["qdrant_counts"] = after
        assert await empty.chunk_entity_relation_graph.get_node("Sensor") is None
        isolated = await empty.aquery_data("How does the Sensor measure temperature?", param=param)
        assert not isolated.get("data", {}).get("chunks")
        report["checks"]["second_workspace_empty"] = True

        # Document the donor's provenance counterexamples in a separate workspace.
        probe = make_rag("provenance")
        await probe.initialize_storages()
        try:
            repeated = fixture()
            repeated["chunks"].append({"content": "Second passage about calibration.",
                                       "source_id": "evidence-A", "chunk_order_index": 8})
            await probe.ainsert_custom_kg(repeated, full_doc_id="document-A-revision-1")
            repeated_node = await probe.chunk_entity_relation_graph.get_node("Sensor")
            last_id = compute_mdhash_id(repeated["chunks"][-1]["content"], prefix="chunk-")
            assert repeated_node["source_id"] == last_id
            report["limitations_observed"]["same_source_alias_keeps_last_chunk"] = True
            duplicate = {"chunks": [{**kg["chunks"][0], "source_id": "evidence-B"}]}
            await probe.ainsert_custom_kg(duplicate, full_doc_id="document-B-revision-1")
            overwritten = await probe.text_chunks.get_by_id(chunk_id)
            assert overwritten["full_doc_id"] == "document-B-revision-1"
            report["limitations_observed"]["identical_content_overwrites_document_provenance"] = True
        finally:
            await probe.finalize_storages()
        assert llm_calls == 0
        report["checks"]["zero_llm_calls"] = True
        report["llm_calls"] = llm_calls
        report["status"] = "passed_with_documented_donor_limitations"
        Path("/tmp/arch001-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"status": report["status"], "checks": report["checks"],
                          "limitations": report["limitations_observed"]}, indent=2))
        client.close()
    finally:
        await empty.finalize_storages()
        await rag.finalize_storages()


if __name__ == "__main__":
    asyncio.run(main())
