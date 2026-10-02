"""Deterministic, offline similarity analysis of already exported chunk vectors."""
from __future__ import annotations
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/analysis/GRAPH_CORPUS_AUDIT"


def norm(v):
    length = math.sqrt(sum(x*x for x in v))
    assert length > 0
    return [x/length for x in v]


def quantiles(xs):
    xs = sorted(xs)
    def q(p):
        pos = (len(xs)-1)*p
        lo = int(pos)
        return xs[lo] + (xs[min(lo+1,len(xs)-1)]-xs[lo])*(pos-lo)
    return {"n":len(xs),"min":xs[0],"median":q(.5),"p75":q(.75),"p90":q(.9),"p95":q(.95),"max":xs[-1]}


def write_csv(name, rows):
    with (OUT/name).open("w",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def main():
    data=json.loads((OUT/"corpus_export.json").read_text(encoding="utf-8"))
    exported=json.loads((OUT/"existing_chunk_vectors.json").read_text(encoding="utf-8"))
    docs=data["documents"]
    chunks={x["id"]:x for x in data["chunks"]}
    vectors=defaultdict(list)
    for p in exported["points"]:
        assert len(p["vector"])==1024 and all(math.isfinite(x) for x in p["vector"])
        assert p["payload"]["revision_id"]==chunks[p["id"]]["revision_id"]
        vectors[p["payload"]["document_id"]].append(norm(p["vector"]))
    # Equal weighting for chunks; their normalized mean is the document vector.
    aggregated={d["id"]:norm([sum(v[k] for v in vectors[d["id"]])/len(vectors[d["id"]]) for k in range(1024)]) for d in docs}
    sims={}
    pairs=[]
    for i,a in enumerate(docs):
        for j in range(i+1,len(docs)):
            b=docs[j]
            s=sum(x*y for x,y in zip(aggregated[a["id"]],aggregated[b["id"]]))
            sims[i,j]=sims[j,i]=s
            pairs.append({"document_a":f"D{i+1:03d}","document_b":f"D{j+1:03d}","document_id_a":a["id"],"document_id_b":b["id"],"title_a":a["title"],"title_b":b["title"],"similarity":s})
    pairs.sort(key=lambda x:(-x["similarity"],x["document_id_a"],x["document_id_b"]))
    nearest=[];nn=[]
    for i,d in enumerate(docs):
        ranks=sorted([j for j in range(len(docs)) if j!=i],key=lambda j:(-sims[i,j],docs[j]["id"]))[:3]
        nn.append(sims[i,ranks[0]])
        for rank,j in enumerate(ranks,1):
            b=docs[j]
            nearest.append({"document":f"D{i+1:03d}","document_id":d["id"],"external_id":d["external_id"],"title":d["title"],"neighbor_rank":rank,"neighbor":f"D{j+1:03d}","neighbor_id":b["id"],"neighbor_external_id":b["external_id"],"neighbor_title":b["title"],"similarity":sims[i,j]})
    write_csv("nearest_documents.csv",nearest)
    write_csv("pairwise_document_similarities.csv",pairs)
    def hist(values):
        bins=[0,.5,.6,.7,.8,.85,.9,.95,1.000001]
        return {f"[{lo},{hi})":sum(lo<=x<hi for x in values) for lo,hi in zip(bins,bins[1:])}
    stats={"snapshot_hash":data["manifest_hash"],"documents":len(docs),"chunks":len(chunks),"sections":dict(Counter(c["section"] for c in chunks.values())),"similarity_method":"L2-normalize existing 1024d Qwen3 chunk vectors, equal-weight mean per frozen revision, L2-normalize mean, cosine; percentile linear interpolation (n-1)*p","qdrant_collection":exported["collection"],"all_pairs":quantiles([p["similarity"] for p in pairs]),"nearest_neighbor":quantiles(nn),"nearest_neighbor_histogram":hist(nn),"all_pairs_histogram":hist([p["similarity"] for p in pairs]),"chunk_vector_export_sha256":hashlib.sha256((OUT/"existing_chunk_vectors.json").read_bytes()).hexdigest()}
    # Sensitivity to short residual chunks: char-length-weighted pooling uses
    # the same existing vectors and changes neither the index nor primary audit.
    weighted_parts=defaultdict(list)
    for p in exported["points"]:
        weighted_parts[p["payload"]["document_id"]].append((norm(p["vector"]),len(chunks[p["id"]]["text"])))
    weighted={did:norm([sum(v[k]*w for v,w in parts)/sum(w for _,w in parts) for k in range(1024)]) for did,parts in weighted_parts.items()}
    alt_pairs=[];alt_sims={};alt_nn=[];same_top1=0
    for i,a in enumerate(docs):
        for j in range(i+1,len(docs)):
            s=sum(x*y for x,y in zip(weighted[a["id"]],weighted[docs[j]["id"]]))
            alt_sims[i,j]=alt_sims[j,i]=s
            alt_pairs.append((s,a["id"],docs[j]["id"]))
    for i in range(len(docs)):
        primary=max((j for j in range(len(docs)) if j!=i),key=lambda j:sims[i,j])
        alternative=max((j for j in range(len(docs)) if j!=i),key=lambda j:alt_sims[i,j])
        same_top1+=primary==alternative;alt_nn.append(alt_sims[i,alternative])
    primary30={(p["document_id_a"],p["document_id_b"]) for p in pairs[:30]}
    alternative30={(a,b) for _,a,b in sorted(alt_pairs,reverse=True)[:30]}
    stats["pooling_sensitivity"]={"alternative":"character-length-weighted normalized chunk mean","nearest_neighbor":quantiles(alt_nn),"same_top1_document_count":same_top1,"same_top30_pair_count":len(primary30&alternative30),"limitation":"Equal-chunk pooling can over-weight short residual chunks; alternative is a sensitivity check, not an independent human similarity gold."}
    (OUT/"similarity_stats.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    text=[]
    for rank,p in enumerate(pairs[:30],1):
        text.append(f"\n## Pair {rank:02d} | {p['document_a']} vs {p['document_b']} | cosine={p['similarity']:.6f}\n")
        for side in ("a","b"):
            d=next(d for d in docs if d["id"]==p["document_id_"+side])
            text.append(f"\n{p['document_'+side]} {d['title']} | {d['external_id']}\n")
            for c in data["chunks"]:
                if c["revision_id"]==d["active_revision_id"]:
                    text.append(f"[chunk={c['id']}] {c['text']}\n")
    (OUT/"top30_pairs_raw_first.txt").write_text("\n".join(text),encoding="utf-8")
    print(json.dumps(stats,ensure_ascii=False))


if __name__=="__main__":main()
