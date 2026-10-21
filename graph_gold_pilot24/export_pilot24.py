"""Read-only export of the 24 frozen OpenAlex document revisions for annotation.

From the root of the original repo (app import available in src):
    DATABASE_URL='postgresql+psycopg://...' \
    python /path/to/export_pilot24.py --manifest /path/to/pilot24_manifest.csv \
         --out /path/to/pilot24_sources.jsonl
No Ollama/Neo4j/Qdrant; only SELECT queries.
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

# Original repo has its importable app in src/; this script is run from repo root.
sys.path.insert(0, str(Path.cwd() / "src"))
from app.storage.models import SourceDocument, DocumentRevision, EvidenceChunk  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--database-env", default="DATABASE_URL")
    args = ap.parse_args()
    db = os.environ.get(args.database_env)
    if not db:
        raise SystemExit(f"Missing environment variable {args.database_env}")
    with args.manifest.open(encoding="utf-8-sig", newline="") as f:
        manifest = list(csv.DictReader(f))
    if len(manifest) != 24 or len({r["document_code"] for r in manifest}) != 24:
        raise SystemExit("Manifest must contain 24 distinct documents")
    if args.out.exists():
        raise SystemExit("Output exists; refusing to overwrite it")
    engine = create_engine(db)
    output = []
    try:
        with Session(engine) as session:
            for row in manifest:
                doc = session.get(SourceDocument, UUID(row["document_id"]))
                rev = session.get(DocumentRevision, UUID(row["revision_id"]))
                if doc is None or rev is None or rev.document_id != doc.id:
                    raise RuntimeError(f"Missing frozen revision: {row['document_code']}")
                if doc.source != "openalex" or doc.external_id != row["openalex_id"]:
                    raise RuntimeError(f"Document ID/source drift: {row['document_code']}")
                chunks = session.scalars(
                    select(EvidenceChunk).where(EvidenceChunk.revision_id == rev.id)
                    .order_by(EvidenceChunk.section, EvidenceChunk.ordinal, EvidenceChunk.id)
                ).all()
                if not chunks:
                    raise RuntimeError(f"Missing EvidenceChunks: {row['document_code']}")
                output.append({
                    "split": row["split"],
                    "document_code": row["document_code"],
                    "document_id": str(doc.id),
                    "revision_id": str(rev.id),
                    "openalex_id": doc.external_id,
                    "source": doc.source,
                    "title": doc.title,
                    "cluster": row["cluster"],
                    "revision_content_hash": rev.content_hash,
                    "chunks": [{
                        "chunk_id": str(c.id),
                        "section": c.section,
                        "ordinal": c.ordinal,
                        "section_start": c.section_start,
                        "section_end": c.section_end,
                        "language": c.language,
                        "stored_chunk_hash": c.hash,
                        "text_sha256": hashlib.sha256(c.text.encode("utf-8")).hexdigest(),
                        "text": c.text,
                    } for c in chunks],
                })
    finally:
        engine.dispose()
    # Atomic write after validation. No DB modifications.
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temp = args.out.with_name(args.out.name + ".tmp")
    try:
        temp.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in output), encoding="utf-8")
        temp.replace(args.out)
    finally:
        if temp.exists(): temp.unlink()
    print(f"Exported {len(output)} document revisions and {sum(len(x['chunks']) for x in output)} chunks to {args.out}")


if __name__ == "__main__":
    main()
