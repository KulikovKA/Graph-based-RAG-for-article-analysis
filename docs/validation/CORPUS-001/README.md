# CORPUS-001 validation

Status: **in progress; 10-document write smoke, idempotency, and resume checks completed**.

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

The Graph extractor runtime profile is output limit 2048, context window 16384,
timeout 300 seconds, temperature 0, and thinking disabled. Extraction batches
remain six chunks, with the bounded `done_reason=length` split fallback retained.
This profile responds to the single-chunk truncation at `num_predict=536`; it
does not change the model, digest, prompt, extractor version, vocabulary
version, or confidence threshold.

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
`EPO_CONSUMER_SECRET`. The `corpus-runner` tools-profile service now joins the
backend and egress networks and uses the project PostgreSQL, Qdrant, Neo4j,
migrations, production model config, and host Ollama endpoint. The earlier
host-side OpenAlex `network_error` was an environment connectivity limitation:
OpenAlex returned candidates from the container runner's egress network.

Runtime smoke on 2026-10-01/02: migrations completed and OpenAlex dry-run
previewed 10 eligible documents without errors. The original profile failed on
`W2922177019` with `done_reason=length` at `num_predict=536`; the revision had
one chunk and no graph facts or ACKs. After rebasing only the checkpoint's
runtime-profile identity (preserving its run ID, cursor, completed IDs, and
counts), a target-only resume with the profile above completed that same
revision and produced 14 graph facts in 68.5 seconds. Resuming the same run
activated 10/10 documents with 10 Qdrant ACKs and 10 Neo4j ACKs. A second run
with the same query and limit reprocessed 10 existing revisions (`new_revision`
false for all), again with 10/10 activation and both ACKs; resuming that
completed checkpoint was a no-op with counts unchanged. The real graph
integration test passed. CORPUS-001 remains in progress; no 100-document pilot
has run.
