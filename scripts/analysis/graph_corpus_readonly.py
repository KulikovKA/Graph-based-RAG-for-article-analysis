"""Export the frozen corpus and existing vectors; never ingest or mutate services.

Only PostgreSQL SELECT in a read-only repeatable-read transaction, Qdrant GET
and POST /points/scroll are used. Outputs are local audit files only.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/analysis/GRAPH_CORPUS_AUDIT"
MANIFEST = ROOT / "data/checkpoints/graph002-live-20261002.snapshot.json"
COLLECTION = "article_analysis_v1_chunks_5ee7692323ffab32c32bfa2b"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frozen = json.loads(MANIFEST.read_text(encoding="utf-8"))["snapshot"]
    ids = [d["revision_id"] for d in frozen["documents"]]
    # UUIDs from the manifest are validated before producing SQL literals.
    from uuid import UUID
    literals = ",".join("'" + str(UUID(x)) + "'::uuid" for x in ids)
    sql = f"""BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_build_object(
 'transaction_read_only', current_setting('transaction_read_only'),
 'active_documents_total', (SELECT count(*) FROM source_documents WHERE active_revision_id IS NOT NULL),
 'documents', (SELECT json_agg(to_jsonb(d) ORDER BY d.id) FROM source_documents d WHERE d.id IN (SELECT document_id FROM document_revisions WHERE id IN ({literals}))),
 'revisions', (SELECT json_agg(to_jsonb(r) ORDER BY r.id) FROM document_revisions r WHERE r.id IN ({literals})),
 'chunks', (SELECT json_agg(to_jsonb(c) ORDER BY c.revision_id,c.section,c.ordinal) FROM evidence_chunks c WHERE c.revision_id IN ({literals})),
 'states', (SELECT json_agg(to_jsonb(s) ORDER BY s.revision_id,s.extractor_version) FROM graph_extraction_states s WHERE s.revision_id IN ({literals})),
 'facts', (SELECT json_agg(to_jsonb(f) ORDER BY f.revision_id,f.id) FROM graph_facts f WHERE f.revision_id IN ({literals}))
); ROLLBACK;"""
    p = subprocess.run(["docker", "exec", "-i", "article-analysis-postgres-1", "psql", "-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-U", "article_app", "-d", "article_analysis"], input=sql, text=True, encoding="utf-8", capture_output=True, check=True)
    data = json.loads(p.stdout)
    assert data["transaction_read_only"] == "on"
    assert len(data["documents"]) == len(ids) == len(data["revisions"]) == 100
    active = {(x["id"], x["active_revision_id"]) for x in data["documents"]}
    assert active == {(x["document_id"], x["revision_id"]) for x in frozen["documents"]}
    frozen_fact_ids = {x["graph_fact_id"] for x in frozen["facts"]}
    matching = [x for x in data["facts"] if x["id"] in frozen_fact_ids]
    assert len(matching) == len(frozen_fact_ids)
    by_id = {x["id"]: x for x in matching}
    assert all(by_id[x["graph_fact_id"]]["to_key"] == x["feature_key"] and by_id[x["graph_fact_id"]]["revision_id"] == x["revision_id"] for x in frozen["facts"])
    data["facts"] = matching
    data["manifest_hash"] = frozen["snapshot_hash"]
    data["exported_at_utc"] = datetime.now(timezone.utc).isoformat()
    data["manifest_sha256"] = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    (OUT / "corpus_export.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Existing container acts only as network reader; no files are created there.
    reader = '''import json, urllib.request
collection = "''' + COLLECTION + '''"
base = "http://qdrant:6333/collections/" + collection
metadata = json.load(urllib.request.urlopen(base))
points = []
offset = None
while True:
    body = {"limit": 256, "with_payload": True, "with_vector": True}
    if offset is not None: body["offset"] = offset
    req = urllib.request.Request(base + "/points/scroll", data=json.dumps(body).encode(), headers={"Content-Type":"application/json"}, method="POST")
    result = json.load(urllib.request.urlopen(req))["result"]
    points.extend(result["points"])
    offset = result.get("next_page_offset")
    if offset is None: break
print(json.dumps({"collection":collection,"metadata":metadata,"points":points}))
'''
    p = subprocess.run(["docker", "exec", "-i", "ui-preview-api", "python", "-"], input=reader, text=True, encoding="utf-8", capture_output=True, check=True)
    vectors = json.loads(p.stdout)
    selected = [x for x in vectors["points"] if x["payload"]["revision_id"] in set(ids)]
    vectors["points_total_before_filter"] = len(vectors["points"])
    vectors["points"] = selected
    assert {x["id"] for x in selected} == {x["id"] for x in data["chunks"]}
    (OUT / "existing_chunk_vectors.json").write_text(json.dumps(vectors) + "\n", encoding="utf-8")
    revisions = {x["id"]: x for x in data["revisions"]}
    chunks = {rid: [x for x in data["chunks"] if x["revision_id"] == rid] for rid in ids}
    text = []
    for i, d in enumerate(data["documents"], 1):
        rid = d["active_revision_id"]
        text.append(f"\n### D{i:03d} | {d['id']} | {d['external_id']}\n{d['title']}\n")
        for c in chunks[rid]:
            text.append(f"[{c['section']} #{c['ordinal']} chunk={c['id']}]\n{c['text']}\n")
    (OUT / "raw_corpus_reading.txt").write_text("\n".join(text), encoding="utf-8")
    print(json.dumps({"documents":len(data["documents"]),"chunks":len(data["chunks"]),"frozen_facts":len(matching),"vectors":len(selected),"snapshot_hash":frozen["snapshot_hash"]}))


if __name__ == "__main__":
    main()
