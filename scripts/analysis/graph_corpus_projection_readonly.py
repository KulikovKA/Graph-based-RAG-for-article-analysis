"""MATCH-only verification of baseline Neo4j projection, no production adapter."""
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"docs/analysis/GRAPH_CORPUS_AUDIT"


def main():
    # Read container config in memory. Never print or save credentials.
    inspected=json.loads(subprocess.run(["docker","inspect","article-analysis-neo4j-1"],capture_output=True,text=True,encoding="utf-8",check=True).stdout)[0]
    env=dict(x.split("=",1) for x in inspected["Config"]["Env"] if "=" in x)
    auth=env.get("NEO4J_AUTH","")
    assert auth and auth!="none"
    user,password=auth.split("/",1)
    code='''import json, sys
from neo4j import GraphDatabase, READ_ACCESS
payload=json.load(sys.stdin)
driver=GraphDatabase.driver("bolt://neo4j:7687",auth=(payload["user"],payload["password"]))
with driver.session(database="neo4j",default_access_mode=READ_ACCESS) as session:
    def read(tx):
        nodes=tx.run("MATCH (n) WHERE n.namespace=$namespace AND (n:ScientificWork OR n:TechnicalFeature OR n:Patent) RETURN n.key AS key,labels(n) AS labels,n.revision_id AS revision_id",namespace=payload["namespace"]).data()
        edges=tx.run("MATCH (a)-[r:DISCLOSES_FEATURE]->(b) WHERE r.namespace=$namespace RETURN r.fact_id AS fact_id,a.key AS source_key,b.key AS feature_key,r.document_revision_id AS revision_id",namespace=payload["namespace"]).data()
        return {"nodes":nodes,"edges":edges,"mode":"execute_read; only MATCH/RETURN"}
    result=session.execute_read(read)
driver.close()
print(json.dumps(result))
'''
    # Pass code via -c (does not include auth), data via standard input.
    payload={"user":user,"password":password,"namespace":"article-analysis-domain-v1"}
    p=subprocess.run(["docker","exec","-i","ui-preview-api","python","-c",code],input=json.dumps(payload),capture_output=True,text=True,encoding="utf-8",check=True)
    projection=json.loads(p.stdout)
    corpus=json.loads((OUT/"corpus_export.json").read_text(encoding="utf-8"))
    facts={f["id"]:f for f in corpus["facts"]}
    assert {e["fact_id"] for e in projection["edges"]}==set(facts)
    assert all(e["feature_key"]==facts[e["fact_id"]]["to_key"] and e["source_key"]==facts[e["fact_id"]]["from_key"] for e in projection["edges"])
    projection["frozen_fact_ids_match"]=True
    (OUT/"neo4j_projection_read.json").write_text(json.dumps(projection,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"nodes":len(projection["nodes"]),"edges":len(projection["edges"]),"fact_ids_match":True}))


if __name__=="__main__":main()
