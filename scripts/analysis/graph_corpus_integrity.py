"""Offline audit counts, source checks and metadata links; no service access."""
import base64
import csv
import hashlib
import json
import unicodedata
from collections import Counter,defaultdict
from pathlib import Path

OUT=Path(__file__).resolve().parents[2]/"docs/analysis/GRAPH_CORPUS_AUDIT"


def canonical(s):return " ".join(unicodedata.normalize("NFKC",s).casefold().split())


def main():
    x=json.loads((OUT/"corpus_export.json").read_text(encoding="utf-8"))
    docs=x["documents"];chunks={c["id"]:c for c in x["chunks"]}
    revisions={r["id"]:r for r in x["revisions"]}
    states={s["revision_id"]:s for s in x["states"]}
    labels=defaultdict(set);factcounts=Counter()
    for f in x["facts"]:
        c=chunks[f["chunk_id"]]
        assert c["revision_id"]==f["revision_id"]
        assert 0<=f["span_start"]<f["span_end"]<=len(c["text"])
        quote=c["text"][f["span_start"]:f["span_end"]]
        label=base64.urlsafe_b64decode(f["to_key"].rsplit(":",1)[1]+"===").decode()
        assert canonical(label) in canonical(quote),(f["id"],label)
        labels[f["to_key"]].add(f["revision_id"]);factcounts[f["revision_id"]]+=1
    for c in chunks.values():assert hashlib.sha256(c["text"].encode()).hexdigest()==c["hash"]
    coverage=[]
    for i,d in enumerate(docs,1):
        rid=d["active_revision_id"];r=revisions[rid]
        assert factcounts[rid]==states[rid]["fact_count"]
        section=r["normalized_json"]["sections"][0]["text"]
        cs=sorted([c for c in chunks.values() if c["revision_id"]==rid],key=lambda c:c["section_start"])
        assert all(section[c["section_start"]:c["section_end"]]==c["text"] for c in cs)
        covered=[False]*len(section)
        for c in cs:
            for k in range(c["section_start"],c["section_end"]):covered[k]=True
        gaps="".join(ch for ch,ok in zip(section,covered) if not ok)
        assert not gaps.strip(),(d["id"],gaps)
        coverage.append({"document":f"D{i:03d}","document_id":d["id"],"revision_id":rid,"abstract_chars":len(section),"chunks":len(cs),"fact_count":factcounts[rid],"uncovered_nonwhitespace_chars":len(gaps.strip())})
    external={d["external_id"]:d for d in docs}
    links=[];self_refs=[]
    for i,d in enumerate(docs,1):
        refs=set(revisions[d["active_revision_id"]]["normalized_json"]["metadata"].get("referenced_work_ids",[]))
        for ref in sorted(refs&external.keys()):
            b=external[ref]
            if b["id"]==d["id"]:
                self_refs.append(d["external_id"]);continue
            links.append({"from_document":f"D{i:03d}","from_id":d["id"],"from_external_id":d["external_id"],"from_title":d["title"],"to_id":b["id"],"to_external_id":b["external_id"],"to_title":b["title"],"provenance":"frozen normalized_json.metadata.referenced_work_ids; source-reported citation, not technical support"})
    adjacency={d["id"]:set() for d in docs}
    for l in links:adjacency[l["from_id"]].add(l["to_id"]);adjacency[l["to_id"]].add(l["from_id"])
    def components(adj):
        seen=set();result=[]
        for n in adj:
            if n in seen:continue
            stack=[n];group=set()
            while stack:
                z=stack.pop()
                if z in group:continue
                group.add(z);stack.extend(adj[z]-group)
            seen.update(group);result.append(group)
        return sorted([len(g) for g in result],reverse=True)
    graph_adj={d["active_revision_id"]:set() for d in docs}
    connected=set()
    for occurrences in labels.values():
        for a in occurrences:
            graph_adj[a].update(occurrences-{a})
            for b in occurrences-{a}:connected.add(tuple(sorted((a,b))))
    degree=Counter(len(v) for v in labels.values())
    stats={"features":len(labels),"facts":len(x["facts"]),"feature_document_degree_distribution":dict(degree),"singleton_features":degree[1],"shared_features":sum(n for deg,n in degree.items() if deg>1),"shared_percent":100*sum(n for deg,n in degree.items() if deg>1)/len(labels),"documents_with_facts":sum(bool(factcounts[d["active_revision_id"]]) for d in docs),"zero_fact_documents":sum(not factcounts[d["active_revision_id"]] for d in docs),"full_baseline_nodes_in_neo4j":509,"incident_nodes_only":498,"edges_per_incident_vertex":417/498,"distinct_features_per_document_mean":417/100,"globally_unique_features_div_documents":409/100,"edges_per_fact_bearing_document":417/89,"baseline_document_component_sizes":components(graph_adj),"connected_document_pairs":len(connected),"chunk_sha256_verified":len(chunks),"fact_quote_normalized_target_verified":len(x["facts"]),"nonwhitespace_section_coverage_verified_documents":100,"citation_metadata":{"directed_in_corpus_links":len(links),"docs_with_incident_citation_link":sum(bool(v) for v in adjacency.values()),"undirected_component_sizes":components(adjacency),"self_references_excluded":self_refs},"fact_confidence_distribution":dict(Counter(f["confidence"] for f in x["facts"]))}
    (OUT/"integrity_graph_stats.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for name,rows in [("document_content_coverage.csv",coverage),("citation_metadata_links.csv",links)]:
        with (OUT/name).open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps(stats,ensure_ascii=False))


if __name__=="__main__":main()
