"""Compile explicitly authored analyst annotations; no model or service writes."""
import base64
import csv
import json
from collections import defaultdict
from pathlib import Path

OUT=Path(__file__).resolve().parents[2]/"docs/analysis/GRAPH_CORPUS_AUDIT"

# Manually selected existing labels corresponding to an annotated common topic.
# Select only content explicit in a label (including narrower material family
# and qualified concept), never infer an antecedent from surrounding quote.
# A selection does not imply alias equality or a standalone concept node.
# Indices are zero-based. This selection rubric is descriptive, not recall gold.
REPRESENTED={
1:({},{0:"gate-free",1:"gate-free",2:"preferential adsorption"}),
2:({1:"b–n codoping"},{}),
3:({3:"6 fold",4:"sensitivity better"},{3:"high sensitivity",4:"detection limit"}),
4:({1:"b–n codoping"},{1:"b- and n-doped",2:"only no and no2",3:"only no and no2"}),
5:({},{}),
6:({},{}),
7:({3:"long recovery"},{0:"wo 3 nanorods",1:"room-temperature gas sensor",2:"highly sensitive",3:"extremely fast recovery",4:"selectivity"}),
8:({1:"b- and n-doped",2:"only no and no2",3:"only no and no2"},{}),
9:({2:"ultrasensitive",3:"single-walled"},{0:"graphene's unique"}),
10:({},{}),
11:({},{0:"2d materials",1:"graphene",2:"transition metal chalcogenides"}),
12:({},{}),
13:({0:"nitrogen-doped",1:"responsive to low",2:"hydrothermal method",3:"increase the gas sensitivity"},{}),
14:({},{}),
15:({1:"first-principles",4:"density of states"},{}),
16:({2:"high sensitivity"},{}),
17:({0:"gate-free",1:"preferential adsorption"},{}),
18:({0:"gate-free",1:"preferential adsorption",2:"gate-free",3:"preferential adsorption"},{0:"charge transfer between gases",1:"charge transfer between graphene and no2",3:"reversible molecular"}),
19:({0:"nitrogen-doped",1:"nitrogen-doped",2:"increase the gas sensitivity",3:"nitrogen-doped"},{0:"3d sulfonated",1:"3d sulfonated"}),
20:({},{}),
21:({},{}),
22:({0:"agglomerated structures",1:"agglomerated structures"},{0:"rutile sno2",1:"rutile sno2",2:"the linear range"}),
23:({},{0:"wo 3 nanorods",1:"room-temperature gas sensor"}),
24:({},{0:"3d sulfonated"}),
25:({2:"great selectivity"},{0:"gate-free"}),
26:({1:"high sensitivity",3:"detection limit"},{0:"gate-free",1:"preferential adsorption",2:"gate-free"}),
27:({},{2:"p-doping",3:"increase in graphene resistance"}),
28:({0:"reduced graphene oxide nanofiber",1:"excellent sensitivity",2:"ultra-sensitive"},{0:"wo 3 nanorods",1:"highly sensitive",2:"room-temperature gas sensor"}),
29:({1:"transparency",2:"flexibility",3:"bending strain",4:"highly sensitive"},{1:"overall device optical",3:"reliable sensing performance"}),
30:({0:"gate-free",2:"gate-free",3:"preferential adsorption"},{2:"p-doping"}),
}


def csv_write(name, rows):
    with (OUT/name).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    data=json.loads((OUT/"corpus_export.json").read_text(encoding="utf-8"))
    annotation=json.loads((OUT/"raw_pair_annotations.json").read_text(encoding="utf-8"))
    pairs=list(csv.DictReader((OUT/"pairwise_document_similarities.csv").open(encoding="utf-8-sig")))[:30]
    docs={x["id"]:x for x in data["documents"]}
    facts=defaultdict(list)
    for f in data["facts"]:
        f={**f,"label":base64.urlsafe_b64decode(f["to_key"].rsplit(":",1)[1]+"===").decode()}
        facts[f["revision_id"]].append(f)
    def locate(did,phrase):
        d=docs[did]
        for c in data["chunks"]:
            if c["revision_id"]==d["active_revision_id"] and phrase in c["text"]:
                start=c["text"].index(phrase)
                return c["id"],start,start+len(phrase)
        raise ValueError((did,phrase))
    summary=[];details=[]
    for a,p in zip(annotation["pairs"],pairs):
        fa=facts[docs[p["document_id_a"]]["active_revision_id"]]
        fb=facts[docs[p["document_id_b"]]["active_revision_id"]]
        shared=sorted({f["label"] for f in fa}&{f["label"] for f in fb})
        absent=[];qualified=[]
        for k,(concept,qa,qb) in enumerate(a["concepts"]):
            represented=[]
            row={"pair_rank":a["rank"],"document_a":p["document_a"],"document_b":p["document_b"],"concept":concept}
            for side,did,quote,fs,mapping in [("a",p["document_id_a"],qa,fa,REPRESENTED[a["rank"]][0]),("b",p["document_id_b"],qb,fb,REPRESENTED[a["rank"]][1])]:
                cid,start,end=locate(did,quote)
                prefix=mapping.get(k)
                match=[f for f in fs if prefix is not None and f["label"].startswith(prefix)]
                if prefix is not None: assert len(match)==1,(a["rank"],k,side,prefix)
                row.update({"quote_"+side:quote,"chunk_id_"+side:cid,"unicode_start_"+side:start,"unicode_end_"+side:end,"selected_fact_id_"+side:match[0]["id"] if match else "","selected_label_"+side:match[0]["label"] if match else ""})
                represented.append(bool(match))
            if all(represented):
                reason="Present only as differing qualified/propositional/material-family facts; needs typed concept projection, not assumed strict alias."
                qualified.append(concept)
            else:
                reason="No manually selected label explicitly naming this topic on " + ("both sides" if not any(represented) else ("A" if not represented[0] else "B")) + "; extraction/coverage, granularity or background-scope policy may contribute. Fact quotes can still mention it. This is not an extractor recall estimate."
                absent.append(concept)
            row["missed_connection_reason"]=reason
            row["claim_scope_caution"]=a["assessment"]
            row["annotation_method"]="analyst_assistant_manual_single_rater"
            row["selected_mapping_basis"]="explicit label content or narrower family/qualified topic; quote context excluded; not strict SAME"
            details.append(row)
        summary.append({"pair_rank":a["rank"],**p,"human_visible_shared_concepts":"; ".join(z[0] for z in a["concepts"]),"shared_concept_count":len(a["concepts"]),"existing_shared_TechnicalFeatures":"; ".join(shared),"existing_shared_feature_count":len(shared),"all_feature_labels_a":"; ".join(f["label"] for f in fa),"all_feature_labels_b":"; ".join(f["label"] for f in fb),"missed_shared_concepts":"; ".join(z[0] for z in a["concepts"]) if not shared else "","coverage_gap_concepts":"; ".join(absent),"different_qualified_representation_concepts":"; ".join(qualified),"same_technology_area":"yes_related_with_scope_differences","assessment":a["assessment"],"reason_if_missed":"; ".join(filter(None,["missing concept in at least one extraction" if absent else "","qualified/propositional representation" if qualified else ""])),"annotation_method":"analyst_assistant_manual_single_rater"})
    csv_write("manual_pair_audit.csv",summary)
    csv_write("manual_concept_details.csv",details)
    print(json.dumps({"pairs":len(summary),"concept_pair_annotations":len(details),"pairs_without_exact_overlap":sum(x["existing_shared_feature_count"]==0 for x in summary),"concepts_missing_at_least_one_selected_fact":sum(not(x["selected_fact_id_a"] and x["selected_fact_id_b"]) for x in details)}))


if __name__=="__main__":main()
