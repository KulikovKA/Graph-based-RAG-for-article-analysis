# CORPUS-001 validation

Status: **in progress; real pilot blocked by unavailable runtime services**.

The prior `micro10/` artifacts remain unchanged and describe an exploratory
2026-10-01 OpenAlex run against the production ingestion, Qdrant indexing,
graph extraction, PostgreSQL fact persistence, Neo4j projection, and ACK gate.
That run activated seven works; the eighth stopped on a truncated extractor
response. It is useful integration evidence, not the requested 100-document
pilot.

The current runner is `scripts/corpus_backfill.py`. It supports OpenAlex search,
source filters, document and batch limits, dry-run, JSON statistics, an atomic
local checkpoint, and strict identity checks on resume. A checkpoint tracks the
source cursor and completed IDs; an item becomes complete only after Qdrant and
Neo4j ACKs have activated its revision. `--max-documents` is capped at 100.
The selected Graph extractor output limit is now 536 tokens. The historical
LLM-003 benchmark continues to record its measured 384-token profile.

Example commands (run from the repository root):

```powershell
python scripts/corpus_backfill.py --source openalex --query "graphene gas sensor" --max-documents 100 --dry-run --checkpoint data/checkpoints/corpus001-dry-run.json --stats-output data/checkpoints/corpus001-dry-run-stats.json
python scripts/corpus_backfill.py --source openalex --query "graphene gas sensor" --max-documents 100 --checkpoint data/checkpoints/corpus001-write.json --stats-output data/checkpoints/corpus001-write-stats.json
python scripts/corpus_backfill.py --source openalex --query "graphene gas sensor" --max-documents 100 --checkpoint data/checkpoints/corpus001-write.json --resume
```

Checkpoints and run statistics belong under ignored `data/`; do not commit them.
The available command currently handles OpenAlex only. EPO pagination/backfill
and `--source all` are not implemented yet. OpenAlex filtering is passed through
to its adapter. A real 100-work run must wait until OpenAlex network access,
PostgreSQL, Qdrant, Neo4j, inference service, and their credentials are
available. Current dry-run, environment preflight, and validation outcome are
recorded in `result.json`.
