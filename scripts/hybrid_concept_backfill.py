"""Controlled HYBRID-001 source-grounded concept extraction runner."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

import httpx
from neo4j import AsyncGraphDatabase
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.domain.inference import InferenceOutputLimit, InferenceProvider  # noqa: E402
from app.integrations.inference_http import OllamaProvider  # noqa: E402
from app.services.technical_concepts import (  # noqa: E402
    CONCEPT_SCHEMA_VERSION,
    TechnicalConceptMentionV1,
    concept_identity,
    validate_or_reanchor_draft,
)
from app.storage.models import (  # noqa: E402
    EvidenceChunk,
    GraphFact,
    SourceDocument,
)
from app.storage.repositories import make_engine  # noqa: E402
from app.workers.inference import GenerationGate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "data/checkpoints/graph002-live-20261002.snapshot.json"
REPORT_DIR = ROOT / "docs/validation/HYBRID-001"
EXTRACTOR_VERSION = "hybrid-technical-concepts-v1.3"
MODEL_ID = "qwen3.5:4b-q4_K_M"
MODEL_DIGEST = "2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd"
MENTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["mentions"],
    "properties": {
        "mentions": {
            "type": "array",
            "maxItems": 12,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "concept_type",
                    "canonical_name",
                    "surface_text",
                    "quote",
                    "start_offset",
                    "end_offset",
                    "qualifiers",
                ],
                "properties": {
                    "concept_type": {
                        "type": "string",
                        "enum": [
                            "MATERIAL",
                            "DEVICE",
                            "PROPERTY",
                            "PERFORMANCE",
                            "ANALYTE",
                            "PROCESS",
                            "MECHANISM",
                            "OPERATING_CONDITION",
                            "MORPHOLOGY",
                            "TECHNOLOGY",
                            "APPLICATION",
                            "OTHER",
                        ],
                    },
                    "canonical_name": {"type": "string", "maxLength": 200},
                    "surface_text": {"type": "string", "maxLength": 240},
                    "quote": {"type": "string", "maxLength": 320},
                    "start_offset": {"type": "integer", "minimum": 0},
                    "end_offset": {"type": "integer", "minimum": 1},
                    "qualifiers": {"type": "object"},
                },
            },
        }
    },
}


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _write_failures(path: Path, failures: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["document_id", "stage", "error"])
        writer.writeheader()
        writer.writerows(failures)


def _stable_id(prefix: str, value: object) -> str:
    del prefix
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _snapshot() -> dict[str, Any]:
    content = cast(dict[str, Any], json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8")))
    snapshot = cast(dict[str, Any], content["snapshot"])
    if (
        len(snapshot["documents"]) != 100
        or snapshot.get("snapshot_hash")
        != "5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0"
    ):
        raise ValueError("frozen GRAPH-002 snapshot identity/count mismatch")
    return snapshot


def _read_docs(sessions: sessionmaker[Session], snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    selected = snapshot["documents"]
    ids = [UUID(row["document_id"]) for row in selected]
    revisions = {row["document_id"]: UUID(row["revision_id"]) for row in selected}
    with sessions() as session:
        documents = session.scalars(select(SourceDocument).where(SourceDocument.id.in_(ids))).all()
        chunks = session.scalars(
            select(EvidenceChunk)
            .where(EvidenceChunk.revision_id.in_(list(revisions.values())))
            .order_by(EvidenceChunk.revision_id, EvidenceChunk.section, EvidenceChunk.ordinal)
        ).all()
        raw_counts: dict[UUID, int] = {
            revision_id: count
            for revision_id, count in session.execute(
                select(GraphFact.revision_id, func.count())
                .where(GraphFact.revision_id.in_(list(revisions.values())))
                .group_by(GraphFact.revision_id)
            ).all()
        }
        doc_by_rev = {str(d.active_revision_id): d for d in documents}
        grouped: dict[str, list[EvidenceChunk]] = {}
        for chunk in chunks:
            grouped.setdefault(str(chunk.revision_id), []).append(chunk)
        output = []
        for row in selected:
            document = doc_by_rev.get(row["revision_id"])
            if document is None or str(document.id) != row["document_id"]:
                raise ValueError("frozen active document/revision mismatch")
            output.append(
                {
                    "document_id": row["document_id"],
                    "revision_id": row["revision_id"],
                    "title": document.title,
                    "chunks": grouped.get(row["revision_id"], []),
                    "raw_feature_count": int(raw_counts.get(revisions[row["document_id"]], 0)),
                }
            )
        if len(output) != 100 or sum(map(lambda d: len(d["chunks"]), output)) != 136:
            raise ValueError("frozen snapshot DB content mismatch (expected 100 docs / 136 chunks)")
        return output


def _make_provider() -> tuple[OllamaProvider, httpx.AsyncClient]:
    if not os.getenv("INFERENCE_BASE_URL"):
        raise RuntimeError("INFERENCE_BASE_URL is required for extraction")
    client = httpx.AsyncClient(
        base_url=os.environ["INFERENCE_BASE_URL"], timeout=httpx.Timeout(300, connect=10)
    )
    provider = OllamaProvider(
        client,
        gate=GenerationGate(waiting_capacity=0),
        model_revisions={MODEL_ID: MODEL_DIGEST},
        supported_efforts={MODEL_ID: set()},
    )
    return provider, client


async def _extract(
    provider: InferenceProvider, chunk: EvidenceChunk
) -> tuple[list[TechnicalConceptMentionV1], float, int, int]:
    prompt = (
        "Extract at most 12 distinct, high-value source-grounded technical concepts "
        "from this chunk. "
        "Return concepts, not propositions. Preserve analyte, process, polarity, "
        "condition and degree "
        "as qualifiers where present. Include only explicit concepts; do not infer omitted facts. "
        "Offsets are zero-based Unicode codepoint offsets into the chunk. quote must be an exact "
        "substring of at most 320 characters and surface_text must be inside quote. "
        "Use the shortest "
        "exact phrase that grounds the surface; do not copy a full sentence or repeat a concept. "
        "Keep base concepts such as selectivity separate from NO2/NH3 and high/low qualifiers. "
        "Empty mentions is valid.\n\n"
        "EVIDENCE CHUNK (JSON string):\n" + json.dumps(chunk.text, ensure_ascii=False)
    )
    started = time.perf_counter()
    async def request(max_output_tokens: int) -> Any:
        return await provider.complete_json(
            model_id=MODEL_ID,
            prompt_version=CONCEPT_SCHEMA_VERSION,
            request_id=f"hybrid-{chunk.id}",
            prompt=prompt,
            timeout=300,
            schema=MENTION_SCHEMA,
            max_output_tokens=max_output_tokens,
            reasoning_effort="default",
            thinking=False,
        )

    request_attempts = 1
    try:
        result = await request(2048)
    except InferenceOutputLimit:
        request_attempts += 1
        result = await request(3072)
    mentions: list[TechnicalConceptMentionV1] = []
    rejects = 0
    for draft in result.value["mentions"]:
        try:
            mention = validate_or_reanchor_draft(draft, chunk.text)
        except (ValidationError, ValueError, TypeError):
            rejects += 1
            continue
        mentions.append(mention)
    return mentions, time.perf_counter() - started, rejects, request_attempts


async def _neo4j_project(rows: list[dict[str, Any]], run_id: UUID) -> int:
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    driver = AsyncGraphDatabase.driver(
        uri, auth=(os.getenv("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"])
    )
    query = """
    UNWIND $rows AS row
    MATCH (d {key: row.document_key})
    WHERE d:ScientificWork AND d.namespace = $namespace
    MERGE (c:TechnicalConcept {concept_id: row.concept_id})
    SET c.concept_type = row.concept_type, c.canonical_name = row.canonical_name,
        c.schema_version = $schema_version, c.namespace = $namespace
    MERGE (d)-[m:MENTIONS_CONCEPT {mention_id: row.mention_id}]->(c)
    SET m.run_id = $run_id, m.revision_id = row.revision_id, m.chunk_id = row.chunk_id,
        m.surface_text = row.surface_text, m.quote = row.quote, m.start_offset = row.start_offset,
        m.end_offset = row.end_offset, m.qualifiers_json = row.qualifiers_json
    RETURN count(m) AS count
    """
    total = 0
    try:
        async with driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:
            await (
                await session.run(
                    "CREATE CONSTRAINT uq_hybrid_concept_id IF NOT EXISTS "
                    "FOR (c:TechnicalConcept) REQUIRE c.concept_id IS UNIQUE"
                )
            ).consume()
            for start in range(0, len(rows), 200):
                records = await (
                    await session.run(
                        query,
                        rows=rows[start : start + 200],
                        run_id=str(run_id),
                        schema_version=CONCEPT_SCHEMA_VERSION,
                        namespace="article-analysis-domain-v1",
                    )
                ).single()
                total += int(records["count"] if records else 0)
        return total
    finally:
        await driver.close()


async def main_async(args: argparse.Namespace) -> int:
    snapshot = _snapshot()
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    if args.report_only:
        raise RuntimeError(
            "report-only requires an existing HYBRID-001 Postgres run; none is configured"
        )
    if args.dry_run:
        print(
            json.dumps(
                {
                    "snapshot_hash": snapshot["snapshot_hash"],
                    "documents": len(snapshot["documents"]),
                    "graph_facts": len(snapshot["facts"]),
                    "chunk_count_expected": 136,
                    "model": MODEL_ID,
                    "model_digest": MODEL_DIGEST,
                    "schema": CONCEPT_SCHEMA_VERSION,
                    "network_or_database_calls": False,
                },
                indent=2,
            )
        )
        return 0
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError(
            "DATABASE_URL is required; the offline audit export is not an extraction source"
        )
    engine = make_engine(os.environ["DATABASE_URL"])
    sessions = sessionmaker(engine, expire_on_commit=False)
    docs = _read_docs(sessions, snapshot)
    if not os.getenv("NEO4J_PASSWORD"):
        raise RuntimeError("NEO4J_PASSWORD is required for isolated shadow projection")
    # The prompt/config identity is fixed to the audited model. Runtime preflight validates digest.
    provider, client = _make_provider()
    tags = await client.get("/api/tags", timeout=10)
    tags.raise_for_status()
    model_rows = tags.json().get("models", [])
    installed = next((row for row in model_rows if row.get("name") == MODEL_ID), None)
    if installed is None or installed.get("digest") != MODEL_DIGEST:
        await client.aclose()
        raise RuntimeError("required semantic model digest is not installed; no pull is attempted")
    run_id = uuid4()
    chosen = docs
    if args.max_documents:
        if args.max_documents == 10:
            audit_path = ROOT / "docs/analysis/GRAPH_CORPUS_AUDIT/zero_fact_audit.csv"
            with audit_path.open(encoding="utf-8-sig", newline="") as source:
                zero_map = {row["doc_no"]: row["document_id"] for row in csv.DictReader(source)}
            selected = {zero_map["D007"], zero_map["D064"]}
            for doc in docs:
                if doc["raw_feature_count"] > 0 and len(selected) < 10:
                    selected.add(doc["document_id"])
            chosen = [d for d in docs if d["document_id"] in selected]
        elif args.max_documents == 100:
            smoke_path = report_dir / "smoke.json"
            if not smoke_path.exists() or not json.loads(
                smoke_path.read_text(encoding="utf-8")
            ).get("passed"):
                raise RuntimeError(
                    "full 100-document run requires a successful recorded 10-document smoke"
                )
        else:
            chosen = docs[: args.max_documents]
    checkpoint_file = Path(args.checkpoint)
    checkpoint = (
        json.loads(checkpoint_file.read_text(encoding="utf-8"))
        if args.resume and checkpoint_file.exists()
        else {
            "snapshot_hash": snapshot["snapshot_hash"],
            "run_id": str(run_id),
            "completed": [],
            "mentions": [],
            "failures": [],
            "latencies": [],
            "llm_calls": 0,
            "validation_rejects": 0,
            "config_identity": {
                "schema_version": CONCEPT_SCHEMA_VERSION,
                "extractor_version": EXTRACTOR_VERSION,
                "model_id": MODEL_ID,
                "model_digest": MODEL_DIGEST,
                "thinking": False,
            },
        }
    )
    if checkpoint["snapshot_hash"] != snapshot["snapshot_hash"]:
        raise ValueError("checkpoint snapshot mismatch")
    expected_config = {
        "schema_version": CONCEPT_SCHEMA_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "model_id": MODEL_ID,
        "model_digest": MODEL_DIGEST,
        "thinking": False,
    }
    if checkpoint.get("config_identity") != expected_config:
        raise ValueError("checkpoint model, schema, or thinking configuration mismatch")
    run_id = UUID(checkpoint["run_id"])
    try:
        with sessions.begin() as session:
            session.execute(
                text(
                    "INSERT INTO semantic_concept_runs "
                    "(id, extractor_version, snapshot_hash, model_id, model_digest, "
                    "config_json, snapshot_json, status) "
                    "VALUES (:id,:v,:h,:m,:d,CAST(:c AS jsonb),CAST(:s AS jsonb),'running') "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": run_id,
                    "v": EXTRACTOR_VERSION,
                    "h": snapshot["snapshot_hash"],
                    "m": MODEL_ID,
                    "d": MODEL_DIGEST,
                    "c": json.dumps({"schema": CONCEPT_SCHEMA_VERSION, "temperature": 0}),
                    "s": json.dumps(snapshot),
                },
            )
            for doc in chosen:
                session.execute(
                    text(
                        "INSERT INTO semantic_concept_run_documents "
                        "(run_id,document_id,revision_id,status) "
                        "VALUES (:r,:d,:v,'pending') ON CONFLICT DO NOTHING"
                    ),
                    {"r": run_id, "d": UUID(doc["document_id"]), "v": UUID(doc["revision_id"])},
                )
        completed = set(checkpoint["completed"])
        total = len(chosen)
        for n, doc in enumerate(chosen, 1):
            print(f"[{n}/{total}] {doc['document_id']} {doc['title'][:90]}", flush=True)
            if doc["document_id"] in completed:
                continue
            valid: list[tuple[EvidenceChunk, TechnicalConceptMentionV1]] = []
            try:
                document_seconds = 0.0
                for chunk in doc["chunks"]:
                    mentions, elapsed, rejects, request_attempts = await _extract(provider, chunk)
                    document_seconds += elapsed
                    checkpoint["llm_calls"] += request_attempts
                    checkpoint["validation_rejects"] += rejects
                    valid.extend((chunk, mention) for mention in mentions)
                rows = []
                for chunk, mention in valid:
                    typ, name = concept_identity(mention)
                    concept_id = _stable_id("tc_", typ + ":" + name)
                    mention_id = _stable_id(
                        "tm_",
                        f"{run_id}:{doc['document_id']}:{chunk.id}:{mention.start_offset}:{mention.end_offset}:{concept_id}",
                    )
                    rows.append(
                        {
                            "concept_id": concept_id,
                            "concept_type": typ,
                            "canonical_name": mention.canonical_name,
                            "normalized_key": typ + ":" + name,
                            "mention_id": mention_id,
                            "document_id": doc["document_id"],
                            "document_key": (
                                f"article-analysis-domain-v1:work:{doc['document_id']}"
                                f":rev:{doc['revision_id']}"
                            ),
                            "revision_id": doc["revision_id"],
                            "chunk_id": str(chunk.id),
                            "surface_text": mention.surface_text,
                            "quote": mention.quote,
                            "start_offset": mention.start_offset,
                            "end_offset": mention.end_offset,
                            "qualifiers": mention.qualifiers,
                            "confidence": mention.confidence,
                            "chunk": chunk,
                        }
                    )
                # Repeated model candidates can resolve to the same exact source mention.
                rows = list({row["mention_id"]: row for row in rows}.values())
                with sessions.begin() as session:
                    for row in rows:
                        session.execute(
                            text(
                                "INSERT INTO technical_concepts "
                                "(id,concept_type,canonical_name,normalized_key,schema_version) "
                                "VALUES (:id,:t,:n,:k,:v) ON CONFLICT (id) DO NOTHING"
                            ),
                            {
                                "id": row["concept_id"],
                                "t": row["concept_type"],
                                "n": row["canonical_name"],
                                "k": row["normalized_key"],
                                "v": CONCEPT_SCHEMA_VERSION,
                            },
                        )
                        session.execute(
                            text(
                                "INSERT INTO concept_mentions "
                                "(id,run_id,concept_id,document_id,revision_id,chunk_id,surface_text,"
                                "quote,start_offset,end_offset,qualifiers_json,confidence,"
                                "extractor_version,model_id,model_digest) "
                                "VALUES (:id,:r,:c,:d,:v,:ch,:surface,:quote,:s,:e,"
                                "CAST(:q AS jsonb),:conf,:x,:m,:md) "
                                "ON CONFLICT (id) DO NOTHING"
                            ),
                            {
                                "id": row["mention_id"],
                                "r": run_id,
                                "c": row["concept_id"],
                                "d": UUID(doc["document_id"]),
                                "v": UUID(doc["revision_id"]),
                                "ch": UUID(row["chunk_id"]),
                                "surface": row["surface_text"],
                                "quote": row["quote"],
                                "s": row["start_offset"],
                                "e": row["end_offset"],
                                "q": json.dumps(row["qualifiers"]),
                                "conf": row["confidence"],
                                "x": EXTRACTOR_VERSION,
                                "m": MODEL_ID,
                                "md": MODEL_DIGEST,
                            },
                        )
                    session.execute(
                        text(
                            "UPDATE semantic_concept_run_documents SET status='completed', "
                            "attempts=attempts+1, error=NULL, updated_at=now() "
                            "WHERE run_id=:r AND document_id=:d"
                        ),
                        {"r": run_id, "d": UUID(doc["document_id"])},
                    )
                checkpoint["mentions"].extend(
                    {k: v for k, v in row.items() if k != "chunk"} for row in rows
                )
                checkpoint["completed"].append(doc["document_id"])
                checkpoint["latencies"].append(document_seconds)
                checkpoint["failures"] = [
                    failure
                    for failure in checkpoint["failures"]
                    if failure["document_id"] != doc["document_id"]
                ]
            except Exception as exc:
                checkpoint["failures"] = [
                    failure
                    for failure in checkpoint["failures"]
                    if failure["document_id"] != doc["document_id"]
                ]
                checkpoint["failures"].append(
                    {"document_id": doc["document_id"], "error": str(exc)[:500]}
                )
                print(f"  FAILED: {str(exc)[:180]}", flush=True)
                with sessions.begin() as session:
                    session.execute(
                        text(
                            "UPDATE semantic_concept_run_documents SET status='failed', "
                            "attempts=attempts+1,error=:e,updated_at=now() "
                            "WHERE run_id=:r AND document_id=:d"
                        ),
                        {"e": str(exc)[:2000], "r": run_id, "d": UUID(doc["document_id"])},
                    )
            _write(checkpoint_file, checkpoint)
        run_complete = len(checkpoint["completed"]) >= len(chosen) and not checkpoint["failures"]
        with sessions.begin() as session:
            session.execute(
                text(
                    "UPDATE semantic_concept_runs SET status=:status, "
                    "completed_at=now() WHERE id=:r"
                ),
                {"status": "completed" if run_complete else "failed", "r": run_id},
            )
        checkpoint["mentions"] = list(
            {row["mention_id"]: row for row in checkpoint["mentions"]}.values()
        )
        _write(checkpoint_file, checkpoint)
        neo_rows = [
            {
                k: row[k]
                for k in (
                    "concept_id",
                    "concept_type",
                    "canonical_name",
                    "mention_id",
                    "document_key",
                    "revision_id",
                    "chunk_id",
                    "surface_text",
                    "quote",
                    "start_offset",
        "end_offset",
                    "qualifiers",
                )
            }
            for row in checkpoint["mentions"]
        ]
        for row in neo_rows:
            row["qualifiers_json"] = json.dumps(row.pop("qualifiers"), ensure_ascii=False)
        projected = await _neo4j_project(neo_rows, run_id) if neo_rows else 0
        seconds = checkpoint["latencies"]
        perf = {
            "llm_calls": checkpoint["llm_calls"],
            "median_sec_per_document": statistics.median(seconds) if seconds else None,
            "p95_sec_per_document": sorted(seconds)[max(0, int(len(seconds) * 0.95) - 1)]
            if seconds
            else None,
            "semantic_extraction_total_sec": sum(seconds),
            "neo4j_projected_mentions": projected,
            "postgres_persistence_sec": None,
            "neo4j_projection_sec": None,
            "peak_process_rss_bytes": None,
        }
        _write(report_dir / "performance.json", perf)
        _write_failures(
            report_dir / "extraction_failures.csv",
            [
                {
                    "document_id": failure["document_id"],
                    "stage": "extraction_or_validation",
                    "error": failure["error"],
                }
                for failure in checkpoint["failures"]
            ],
        )
        if len(chosen) == 10:
            smoke = {
                "snapshot_hash": snapshot["snapshot_hash"],
                "run_id": str(run_id),
                "attempted_documents": len(chosen),
                "successful_documents": len(checkpoint["completed"]),
                "zero_fact_documents_included": sum(d["raw_feature_count"] == 0 for d in chosen),
                "mentions": len(checkpoint["mentions"]),
                "validation_rejects": checkpoint["validation_rejects"],
                "passed": len(checkpoint["completed"]) == 10
                and sum(d["raw_feature_count"] == 0 for d in chosen) >= 2
                and bool(checkpoint["mentions"])
                and not checkpoint["failures"],
            }
            _write(report_dir / "smoke.json", smoke)
        _write(
            report_dir / "hybrid_metrics.json",
            {
                "snapshot_hash": snapshot["snapshot_hash"],
                "run_id": str(run_id),
                "attempted_documents": len(chosen),
                "successful_documents": len(checkpoint["completed"]),
                "failed_documents": len(checkpoint["failures"]),
                "total_mentions": len(checkpoint["mentions"]),
                "validation_rejects": checkpoint["validation_rejects"],
                "status": "complete"
                if len(chosen) == 100 and not checkpoint["failures"]
                else "partial",
            },
        )
        return 0 if not checkpoint["failures"] else 2
    finally:
        await client.aclose()
        engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-documents", type=int, choices=(1, 10, 100))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--reset-shadow", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--checkpoint", default="data/checkpoints/hybrid-001.json")
    parser.add_argument("--report-dir", default=str(REPORT_DIR))
    args = parser.parse_args()
    if args.max_documents is not None and args.max_documents < 1:
        parser.error("--max-documents must be positive")
    if args.reset_shadow:
        parser.error(
            "--reset-shadow is intentionally disabled; use a new run ID to preserve provenance"
        )
    return args


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main_async(parse_args())))
