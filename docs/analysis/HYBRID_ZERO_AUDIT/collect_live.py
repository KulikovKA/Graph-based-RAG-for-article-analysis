"""Read-only HYBRID-002 collection. Run inside the existing API container.

Prints source/concept audit data only; never prints credentials or provider bodies.
No extraction, projection, model requests, schema or data writes.
"""

import json
import os
from datetime import UTC, datetime

from neo4j import READ_ACCESS, GraphDatabase
from sqlalchemy import create_engine, text

RUN = "d895217d-ebbe-4117-9066-8ae0ebcd0bdc"


def main():
    engine = create_engine(
        os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1)
    )
    out = {"run_id": RUN, "collected_at_utc": datetime.now(UTC).isoformat()}
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            out["transaction_read_only"] = connection.execute(
                text("SHOW transaction_read_only")
            ).scalar_one()
            queries = {
                "runs": (
                    "SELECT id,extractor_version,snapshot_hash,model_id,model_digest,"
                    "config_json,status,started_at,completed_at FROM semantic_concept_runs "
                    "ORDER BY started_at"
                ),
                "run_documents": (
                    "SELECT * FROM semantic_concept_run_documents WHERE run_id=:run "
                    "ORDER BY document_id"
                ),
                "mentions": (
                    "SELECT m.*,c.concept_type,c.canonical_name,c.normalized_key,c.schema_version "
                    "FROM concept_mentions m JOIN technical_concepts c ON c.id=m.concept_id "
                    "WHERE m.run_id=:run ORDER BY m.id"
                ),
                "documents": (
                    "SELECT d.* FROM source_documents d JOIN semantic_concept_run_documents r "
                    "ON r.document_id=d.id WHERE r.run_id=:run ORDER BY d.id"
                ),
                "revisions": (
                    "SELECT v.* FROM document_revisions v JOIN semantic_concept_run_documents r "
                    "ON r.revision_id=v.id WHERE r.run_id=:run ORDER BY v.id"
                ),
                "chunks": (
                    "SELECT c.* FROM evidence_chunks c JOIN semantic_concept_run_documents r "
                    "ON r.revision_id=c.revision_id WHERE r.run_id=:run "
                    "ORDER BY c.revision_id,c.ordinal"
                ),
                "facts": (
                    "SELECT f.* FROM graph_facts f JOIN semantic_concept_run_documents r "
                    "ON r.revision_id=f.revision_id WHERE r.run_id=:run ORDER BY f.id"
                ),
                "diagnostic_columns": (
                    "SELECT table_name,column_name,data_type FROM information_schema.columns "
                    "WHERE table_schema='public' AND (table_name LIKE '%concept%' "
                    "OR column_name LIKE '%reject%' OR column_name LIKE '%candidate%' "
                    "OR column_name LIKE '%inference%') ORDER BY table_name,ordinal_position"
                ),
                "table_inventory": (
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public' ORDER BY table_name"
                ),
            }
            for key, query in queries.items():
                out[key] = [
                    dict(row) for row in connection.execute(text(query), {"run": RUN}).mappings()
                ]
    engine.dispose()
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    queries = {
        "neo_documents": (
            "MATCH (d:ScientificWork) WHERE d.namespace=$ns "
            "RETURN d.key AS key,properties(d) AS properties ORDER BY key"
        ),
        "neo_mentions": (
            "MATCH (d:ScientificWork)-[m:MENTIONS_CONCEPT]->(c:TechnicalConcept) "
            "WHERE m.run_id=$run RETURN d.key AS document_key,c.concept_id AS concept_id,"
            "properties(m) AS mention,properties(c) AS concept ORDER BY mention.mention_id"
        ),
        "neo_counts": (
            "MATCH (d:ScientificWork) WHERE d.namespace=$ns "
            "OPTIONAL MATCH (d)-[r:DISCLOSES_FEATURE]->(f) "
            "RETURN count(DISTINCT d) AS documents,count(r) AS raw_edges,"
            "count(DISTINCT f) AS raw_features"
        ),
    }
    with driver.session(
        database=os.environ.get("NEO4J_DATABASE", "neo4j"), default_access_mode=READ_ACCESS
    ) as session:
        for key, query in queries.items():
            out[key] = session.execute_read(
                lambda tx, query=query: tx.run(
                    query, ns="article-analysis-domain-v1", run=RUN
                ).data()
            )
    driver.close()
    print(json.dumps(out, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()
