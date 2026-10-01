# CORPUS-001 validation

Status: **in progress; runner extended, real pilot blocked by runtime credentials and database access**.

The prior `micro10/` artifacts remain unchanged and describe an exploratory
2026-10-01 OpenAlex run against the production ingestion, Qdrant indexing,
graph extraction, PostgreSQL fact persistence, Neo4j projection, and ACK gate.
That run activated seven works; the eighth stopped on a truncated extractor
response. It is useful integration evidence, not the requested 100-document
pilot.

The current runner is `scripts/corpus_backfill.py`. It uses the existing
OpenAlex and EPO adapters and the shared production ingestion, indexing,
graph-projection, ACK, and activation services. It supports `--source openalex`,
`--source epo`, and `--source all`; `all` divides the requested total between
the sources, and falls back to OpenAlex for the full limit when EPO credentials
are absent. EPO search uses OPS range pagination (up to 100 results per request)
and accepts an OPS CQL expression through `--filter`.

Dry-run discovers and fetches candidates without writing checkpoints or stats
files. Its `previewed` count is separate from `ingested`. Write-run checkpoints
track completed external IDs only after both index ACKs and activation, and
resume rejects drift in source/query/filter/limits, model digests, extractor,
vocabulary, and projection versions. `--max-documents` is capped at 100.

The Graph extractor stays at the LLM-003 validated 384-token output profile.
The 536-token change had no separate frozen benchmark and was reverted.

Example commands (run from the repository root):

```powershell
python scripts/corpus_backfill.py --source openalex --query "graphene gas sensor" --max-documents 100 --dry-run --checkpoint data/checkpoints/corpus001-dry-run.json --stats-output data/checkpoints/corpus001-dry-run-stats.json
python scripts/corpus_backfill.py --source openalex --query "graphene gas sensor" --max-documents 100 --checkpoint data/checkpoints/corpus001-write.json --stats-output data/checkpoints/corpus001-write-stats.json
python scripts/corpus_backfill.py --source openalex --query "graphene gas sensor" --max-documents 100 --checkpoint data/checkpoints/corpus001-write.json --resume
python scripts/corpus_backfill.py --source epo --query "graphene gas sensor" --max-documents 10 --dry-run
python scripts/corpus_backfill.py --source all --query "graphene gas sensor" --max-documents 100 --dry-run
```

Checkpoints and run statistics belong under ignored `data/`; do not commit them.
EPO credentials are read only from `EPO_CONSUMER_KEY` and
`EPO_CONSUMER_SECRET`. The current OpenAlex dry-run still ends with
`network_error`. In this session `.env` and runtime credentials were absent;
Docker was inaccessible, PostgreSQL rejected the repository's local development
credentials, and Neo4j rejected them. The reachable Qdrant and inference HTTP
services could not be tied to the project's intended deployment. No write run
was attempted. The successful micro10 record remains historical evidence only.
