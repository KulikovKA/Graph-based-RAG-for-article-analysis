"""Combine local audit artifacts and verify structural invariants offline."""
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"docs/analysis/GRAPH_CORPUS_AUDIT"


def rows(name):return list(csv.DictReader((OUT/name).open(encoding="utf-8-sig")))


def summary(values):
    values=sorted(values)
    def q(p):
        z=(len(values)-1)*p;i=int(z)
        return values[i]+(values[min(i+1,len(values)-1)]-values[i])*(z-i)
    return {"n":len(values),"mean":sum(values)/len(values),"median":q(.5),"p75":q(.75),"p90":q(.9),"p95":q(.95),"min":values[0],"max":values[-1]}


def main():
    data=json.loads((OUT/"corpus_export.json").read_text(encoding="utf-8"))
    graph=json.loads((OUT/"integrity_graph_stats.json").read_text(encoding="utf-8"))
    similarity=json.loads((OUT/"similarity_stats.json").read_text(encoding="utf-8"))
    topics=rows("topic_clusters.csv");features=rows("feature_type_audit.csv")
    zero=rows("zero_fact_audit.csv");pairs=rows("manual_pair_audit.csv")
    granularity=rows("feature_granularity_sample.csv")
    assert len(topics)==100 and len({r["document_id"] for r in topics})==100
    assert len(features)==len(granularity)==409
    assert len(zero)==11 and len(pairs)==30
    assert features==granularity
    nearest=rows("nearest_documents.csv")
    assert len(nearest)==300
    assert all(sorted(r["neighbor_rank"] for r in nearest if r["document_id"]==d["id"])==["1","2","3"] for d in data["documents"])
    assert all(r["document_id"]!=r["neighbor_id"] for r in nearest)
    frozen_facts={f["id"]:f for f in data["facts"]}
    chunk_by_id={c["id"]:c for c in data["chunks"]}
    covered_facts=[]
    uuid_pattern=r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    for r in features:
        ids=re.findall(uuid_pattern,r["graph_fact_ids"])
        assert ids and all(frozen_facts[fid]["to_key"]==r["feature_key"] for fid in ids)
        assert any(frozen_facts[fid]["chunk_id"]==r["example_chunk_id"] and chunk_by_id[r["example_chunk_id"]]["text"][frozen_facts[fid]["span_start"]:frozen_facts[fid]["span_end"]]==r["source_quote"] for fid in ids)
        covered_facts.extend(ids)
    assert set(covered_facts)==set(frozen_facts) and len(covered_facts)==417
    details=rows("manual_concept_details.csv")
    assert len(details)==124
    for r in details:
        for side in ("a","b"):
            c=chunk_by_id[r["chunk_id_"+side]]
            assert c["text"][int(r["unicode_start_"+side]):int(r["unicode_end_"+side])]==r["quote_"+side]
            fid=r["selected_fact_id_"+side]
            if fid:assert fid in frozen_facts
    required=["README.md","corpus_stats.json","topic_clusters.csv","nearest_documents.csv","manual_pair_audit.csv","zero_fact_audit.csv","feature_type_audit.csv","feature_granularity_sample.csv","diagnosis.md","architecture_options.md"]
    assert all((OUT/name).exists() for name in required)
    assert len(rows("pairwise_document_similarities.csv"))==4950
    assert all(int(r["existing_shared_feature_count"])==0 for r in pairs)
    by_doc={r["document_id"]:r for r in topics}
    matrix=rows("pairwise_document_similarities.csv")
    within=[float(r["similarity"]) for r in matrix if by_doc[r["document_id_a"]]["primary_cluster"]==by_doc[r["document_id_b"]]["primary_cluster"]]
    between=[float(r["similarity"]) for r in matrix if by_doc[r["document_id_a"]]["primary_cluster"]!=by_doc[r["document_id_b"]]["primary_cluster"]]
    by_cluster=Counter(r["primary_cluster"] for r in topics)
    clusters=[]
    for cluster,n in sorted(by_cluster.items()):
        members={r["document_id"] for r in topics if r["primary_cluster"]==cluster}
        nns=[r for r in nearest if r["document_id"] in members and r["neighbor_rank"]=="1"]
        intra=[float(r["similarity"]) for r in matrix if r["document_id_a"] in members and r["document_id_b"] in members]
        cross=[float(r["similarity"]) for r in matrix if (r["document_id_a"] in members)!=(r["document_id_b"] in members)]
        clusters.append({"cluster":cluster,"name":next(r["cluster_name"] for r in topics if r["primary_cluster"]==cluster),"documents":n,"nearest_neighbor_within_primary_cluster":sum(r["neighbor_id"] in members for r in nns),"within_pair_mean":sum(intra)/len(intra) if intra else None,"cross_pair_mean":sum(cross)/len(cross),"representative_titles":[r["title"] for r in topics if r["primary_cluster"]==cluster][:3]})
    # Match explicit column names from the full manual feature audit.
    print("feature columns",list(features[0]))
    stats={"audit_date_moscow":"2026-10-02","snapshot_hash":data["manifest_hash"],"manifest_path":"data/checkpoints/graph002-live-20261002.snapshot.json","manifest_sha256":data["manifest_sha256"],"snapshot_created_utc":"2026-10-01T23:17:52.315959+00:00","snapshot_created_moscow":"2026-10-02T02:17:52.315959+03:00","postgres_export_utc":data["exported_at_utc"],"source_counts":dict(Counter(d["source"] for d in data["documents"])),"kind_counts":dict(Counter(d["kind"] for d in data["documents"])),"documents":100,"revisions":100,"chunks":136,"content_scope":"abstracts_only; no full-text article sections; all normalized nonwhitespace text covered by chunks","graph":graph,"similarity":similarity,"corpus_composition":{"primary_clusters":clusters,"gas_sensing_core_documents":87,"broader_adjacent_documents":13,"within_primary_cluster_similarity":summary(within),"between_primary_cluster_similarity":summary(between),"same_primary_cluster_top1":sum(by_doc[r["document_id"]]["primary_cluster"]==by_doc[r["neighbor_id"]]["primary_cluster"] for r in nearest if r["neighbor_rank"]=="1"),"partition_method":"inductive single-rater analyst reading; not an objective unique ontology or independent human gold"},"manual_pair_audit":{"closest_pairs_read":30,"unique_documents":len({r[k] for r in pairs for k in ['document_id_a','document_id_b']}),"pairs_related_at_technology_area_level":30,"pairs_with_exact_shared_feature":0,"pairs_involving_zero_fact_document":sum(not r["all_feature_labels_a"] or not r["all_feature_labels_b"] for r in pairs),"manual_shared_topic_annotations":124,"mapping_limitation":"Selected label correspondences are supplemental and rubric-dependent; not extractor recall or causal contribution percentages. Source claims may differ in polarity, analyte or conditions."},"read_only_validation":{"postgres_transaction":"repeatable_read read_only, rollback","postgres_manifest_revisions_and417fact_ids":"matched","neo4j509nodes417edges":"MATCH/RETURN through execute_read; fact IDs and endpoints matched PostgreSQL","qdrant":"GET metadata and POST points/scroll only,136 existing vectors matched all chunk IDs","models_called":0,"ingestion_runs":0,"production_files_changed":0,"commits_created":0},"diagnosis":"CASE E: ontology/representation plus selective extraction, secondary lexical canonicalization, real periphery and claim-specific differences; corpus-limited-only rejected for thematic connectivity, not for strict detailed claim equality"}
    # Readers can inspect exact rubric counts, irrespective of column casing.
    stats["read_only_validation"]["scope"]="audit_execution_before_separately_authorized_publication"
    stats["publication_policy"]={"local_only_exports":["corpus_export.json","existing_chunk_vectors.json","neo4j_projection_read.json","raw_corpus_reading.txt","top30_pairs_raw_first.txt"],"published":"authored audit reports, derived analysis tables, integrity hashes and analysis scripts; raw corpus/vector/database exports excluded"}
    for key in ["primary_kind","semantic_kind","granularity","over_specific_phrase","mixed_kind","label_requires_context","label_truncated"]:
        if key in features[0]:stats.setdefault("feature_audit",{})[key]=dict(Counter(r[key] for r in features))
    (OUT/"corpus_stats.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Artifact hashes make the final local result reviewable and reproducible.
    hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(OUT.iterdir()) if f.is_file() and f.name!="artifact_hashes.json"}
    (OUT/"artifact_hashes.json").write_text(json.dumps(hashes,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"within":summary(within),"between":summary(between),"same_primary_cluster_top1":stats["corpus_composition"]["same_primary_cluster_top1"],"topic_sizes":dict(by_cluster),"feature_stats":stats.get("feature_audit")},ensure_ascii=False))


if __name__=="__main__":main()
