"""Seal ontology v1.0 after a content commit; no evaluation inputs are read.

The manifest pins a prior content commit to avoid a self-referential Git hash.
Commit the resulting manifest separately; it must not rewrite sealed content.
"""
import hashlib
import json
import subprocess
from pathlib import Path

BASE=Path(__file__).resolve().parent
ROOT=BASE.parent
SPEC=BASE/'ontology/v1.0'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target=SPEC/'FREEZE_MANIFEST.json'
    if target.exists():raise SystemExit('Freeze manifest already exists; refusing to rewrite a sealed identity')
    ontology=json.loads((SPEC/'ontology.json').read_text(encoding='utf-8'))
    assert ontology['ontology_id']=='pilot24-ontology-v1.0'
    assert ontology['status']=='TECHNICALLY_FROZEN_PENDING_HUMAN_APPROVAL'
    assert b'????' not in (SPEC/'ontology.json').read_bytes()
    content_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    artifacts={}
    for p in sorted(SPEC.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts or p.name.endswith('.pyc') or p.name==target.name:continue
        name=p.relative_to(SPEC).as_posix()
        gitname=p.relative_to(ROOT).as_posix()
        stored=subprocess.check_output(['git','show',content_commit+':'+gitname],cwd=ROOT)
        assert hashlib.sha256(stored).hexdigest()==sha(p),'Uncommitted ontology artifact: '+name
        artifacts[name]=sha(p)
    tools=['validate_annotations.py','validate_ontology_v1.py','test_ontology_v1.py','freeze_ontology_v1.py']
    tooling={}
    for name in tools:
        p=BASE/name
        stored=subprocess.check_output(['git','show',content_commit+':'+p.relative_to(ROOT).as_posix()],cwd=ROOT)
        assert hashlib.sha256(stored).hexdigest()==sha(p),'Uncommitted tooling: '+name
        tooling[name]=sha(p)
    source_rows=[json.loads(line) for line in (SPEC/'dev_sources.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    assert len(source_rows)==12 and all(d['split']=='DEV' for d in source_rows)
    report=json.loads((SPEC/'validation_report.json').read_text(encoding='utf-8'))
    assert len(report)==12 and all(r['status']=='PASS' for r in report)
    decisions=[json.loads(line) for line in (SPEC/'adjudication_decisions.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    manifest={'ontology_id':ontology['ontology_id'],'status':ontology['status'],
        'content_commit_sha':content_commit,'baseline_commit_sha':'5cee979805fb5e6aa8980d0371e4f5a789139ec7',
        'git_identity_policy':'The content commit is pinned. This manifest is committed next, avoiding a self-referential SHA.',
        'ontology_sha256':sha(SPEC/'ontology.json'),'schema_sha256':sha(SPEC/'annotation.schema.json'),
        'artifact_sha256':artifacts,'tooling_sha256':tooling,
        'dev_source_snapshot':{'source_jsonl_sha256':sha(SPEC/'dev_sources.jsonl'),
            'documents':[{'document_code':d['document_code'],'document_id':d['document_id'],'revision_id':d['revision_id'],
                          'revision_content_hash':d['revision_content_hash'],
                          'chunk_text_sha256':{c['chunk_id']:c['text_sha256'] for c in d['chunks']}} for d in source_rows]},
        'approval_states':{
            'individual_user_decisions':'Recorded as schema constraints; not label human review.',
            'remaining_dev_adjudication':{'actor':'AI','file':'adjudication_decisions.jsonl','records':len(decisions)},
            'technical_freeze':{'actor':'AI','status':'FROZEN'},
            'final_human_ontology_approval':{'status':'PENDING','decision_ref':None},
            'gold_labels':{'human_review':'NOT_REVIEWED','approved_documents':0}},
        'isolation_limitations':['Root conversation previously exposed CALIBRATION/HOLDOUT.',
            'Semantic v1.0 design delegated to a fresh DEV-only context; inherited baseline annotations may retain prior-context influence.',
            'Historical 0.3 freeze first write failed before calibration text display; no retroactive independence claim.']}
    target.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Sealed',ontology['ontology_id'],'content commit',content_commit,'artifacts',len(artifacts))


if __name__=='__main__':main()
