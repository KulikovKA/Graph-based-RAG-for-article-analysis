# CORPUS-001 validation

Status: **in progress; runner runtime wired, 10-document write smoke partially completed**.

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

The Graph extractor uses a 536-token output limit. The 384-token limit had
caused three document extraction failures from insufficient output budget;
536 is the practical corpus-extraction workaround. This changes no model,
prompt, digest, or extractor version and is not a new model-selection benchmark.

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

Runtime smoke on 2026-10-01: migrations completed and OpenAlex dry-run previewed
10 eligible documents without errors. The subsequent `--max-documents 10`
write run activated 7 documents with Qdrant and Neo4j ACKs, then failed on the
next document during graph extraction with `InferenceProtocolError: provider
output did not finish` (run `corpus-20261001T203122Z-81c4e038`). No 100-document
pilot has been run; investigate the remaining extractor failure before resuming.
