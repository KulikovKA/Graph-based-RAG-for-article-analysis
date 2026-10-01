# CORPUS-001 OpenAlex micro10

Status: **runner implemented; end-to-end run pending local services**. This is an
exploratory smoke run and does not complete `CORPUS-001`.

The runner uses `OpenAlexClient`, `IngestionService`, `IndexingService`,
`GraphIndexingService`, the configured Qwen graph model and the production
deterministic quote/span validator. It does not invoke Planner or Analyst. Each
event is emitted as one JSON object with a run ID and stage.

Run a source-only preview first:

```powershell
$env:OPENALEX_API_KEY = "..." # optional
python scripts/corpus_backfill.py --source openalex --query "graphene gas sensor" --max-documents 10 --dry-run
```

For the write run, start PostgreSQL, Qdrant, and Neo4j, build the API image for
the one-off runner, and keep the local inference server available:

```powershell
docker compose -f compose.yaml -f compose.corpus-micro10.yaml -f compose.neo4j-browser.yaml --profile browser up -d postgres qdrant neo4j neo4j-browser-proxy neo4j-bolt-proxy
docker compose build api
docker compose -f compose.yaml -f compose.corpus-micro10.yaml -f compose.neo4j-browser.yaml run --rm migrate
docker compose -f compose.yaml -f compose.corpus-micro10.yaml -f compose.neo4j-browser.yaml --profile tools run --rm corpus-runner --source openalex --query "graphene gas sensor" --max-documents 10
```

Compose passes local `.env` credentials to the isolated runner; PostgreSQL and
Qdrant stay private on the backend network. The browser override uses
loopback-only TCP proxies on the egress network to forward Browser and Bolt to
Neo4j on the private backend network.
Repeat it with the same query to inspect idempotency. The runner caps
`--max-documents` at 100; this pilot uses 10. It skips works without a usable
abstract and continues through search pages until the requested number of
eligible works is reached.

## Run outcome

The live preview fetched 20 works, skipped 10 with missing or short abstracts,
and found 10 eligible candidates. The write search then returned a different
page sequence. It fetched 16 works, skipped 8, ingested 8, indexed 7, and
projected 7. Graph extraction stopped on `W2922177019` because Qwen ended its
JSON response at the configured 384-token limit. That revision remains in
PostgreSQL as `normalized`; its 1 Qdrant point exists, but it has no graph
facts, Neo4j node, ACK, or active generation. The incomplete response was
rejected instead of being stored as an empty extraction. `result.json` contains
the eight write-run works, counts, five exact provenance checks, and the
suspect background-context fact. No abstracts or full corpus are checked in.

The identical query/limit rerun created no new revisions or duplicate points
for the seven fully projected works; their Neo4j counts remained stable. The
eighth work failed at the same model output limit. This partial retry check does
not count as a successful ten-document run.

`CORPUS-001` remains open. Do not scale beyond this ten-document review before
reviewing a successful run and the suspicious background-context fact.

## Neo4j Browser

The separate `compose.neo4j-browser.yaml` override binds Browser and Bolt only
to loopback. With the stack running, start it using:

```powershell
docker compose -f compose.yaml -f compose.neo4j-browser.yaml --profile browser up -d neo4j neo4j-browser-proxy neo4j-bolt-proxy
```

The usual ports 7474 and 7687 serve a different Neo4j 5.12 instance on this
machine. The override uses loopback-only TCP proxies on unused ports for the
pilot database. Browser URL: <http://127.0.0.1:17474/browser/>. Connect with
Bolt URL `bolt://127.0.0.1:17687`, user `neo4j`, and the local password from
`.env`.

All pilot work nodes use the graph namespace configured by
`GRAPH_NAMESPACE` (default `article-analysis-domain-v1`). The current schema
does not attach a pilot run ID to graph nodes, so these queries visualize the
namespace graph:

```cypher
MATCH p=(d)-[:DISCLOSES_FEATURE]->(f:TechnicalFeature)
WHERE d:ScientificWork OR d:Patent
RETURN p
LIMIT 100
```

```cypher
MATCH (d)-[:DISCLOSES_FEATURE]->(f:TechnicalFeature)
WITH f, collect(d) AS docs
WHERE size(docs) > 1
UNWIND docs AS d
RETURN d, f
```

Pilot-scoped Neo4j node and relationship counts (the revision IDs include the
seven projected pilot works):

```cypher
CALL {
  MATCH (d:ScientificWork)
  WHERE d.namespace = 'article-analysis-domain-v1'
    AND d.revision_id IN [
      'c3cd4135-33ed-473f-a24d-9c3bf736b0e9',
      '978dce12-735d-431e-be83-362972cddcd6',
      '5d78f622-9582-4379-86bc-349d581c6c09',
      '608b8803-0460-4606-a870-e3251f1c2146',
      '85c8c16f-76e7-45fb-a9b2-6124974a51e9',
      '6157efd9-fab8-401a-8da8-229bdcd8932f',
      'a3e894f8-6038-4f34-afcd-abd0dac7afa5'
    ]
  RETURN count(d) AS ScientificWork
}
CALL {
  MATCH (d:ScientificWork)-[r:DISCLOSES_FEATURE]->(f:TechnicalFeature)
  WHERE d.namespace = 'article-analysis-domain-v1'
    AND d.revision_id IN [
      'c3cd4135-33ed-473f-a24d-9c3bf736b0e9',
      '978dce12-735d-431e-be83-362972cddcd6',
      '5d78f622-9582-4379-86bc-349d581c6c09',
      '608b8803-0460-4606-a870-e3251f1c2146',
      '85c8c16f-76e7-45fb-a9b2-6124974a51e9',
      '6157efd9-fab8-401a-8da8-229bdcd8932f',
      'a3e894f8-6038-4f34-afcd-abd0dac7afa5'
    ]
  RETURN count(DISTINCT f) AS TechnicalFeature, count(r) AS DISCLOSES_FEATURE
}
RETURN ScientificWork, TechnicalFeature, DISCLOSES_FEATURE
```

```cypher
MATCH (n)
WHERE n.namespace = 'article-analysis-domain-v1'
WITH labels(n) AS labels, count(*) AS nodes
OPTIONAL MATCH (a)-[r]->(b)
WHERE a.namespace = 'article-analysis-domain-v1'
  AND b.namespace = 'article-analysis-domain-v1'
RETURN labels, nodes, type(r) AS relationship, count(r) AS relationships
```

## Validation record

See `result.json` for baseline SHA, run status, counters, configuration
identities, tests, and infrastructure availability. No model, prompt, or gold
data was changed.
