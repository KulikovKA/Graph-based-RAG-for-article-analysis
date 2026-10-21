"""Freeze the 18-type automatic-pass schema after source-only DEV curation."""
import hashlib
import json
from collections import Counter
from pathlib import Path

from build_dev_pair import BASE
from validate_annotations import read_jsonl

path=BASE/'annotations/reviews/relation_vocabulary.json'
v=json.loads(path.read_text(encoding='utf-8'))
if v.get('frozen'):
    print('Schema already frozen; preserving its definitions and recorded chronology.')
    raise SystemExit(0)
drafts=[read_jsonl(p)[0] for p in sorted((BASE/'annotations/drafts').glob('*.jsonl'))]
assert len(drafts)==12 and all(d['split']=='DEV' for d in drafts)
used=Counter(a['relation_type'] for d in drafts for a in d['assertions'])
proposed=Counter(q['proposed_relation_type'] for d in drafts for q in d['unresolved'])
v.update(version='pilot24-rubric-0.3-AUTO-FROZEN',frozen=True,
         status='TEMPORARY_FROZEN_FOR_AUTOMATIC_CALIBRATION_HOLDOUT',
         final_human_ontology_approved=False,freeze_id='pilot24-auto-freeze-0.3',
         freeze_basis='18 approved types fixed from DEV. First freeze persistence failed on a filesystem write before calibration text was displayed; persistence retried without changing any relation definition. Evaluation text was not used to extend or tune the schema.')
assert len(v['relations'])==18
for d in drafts:
    d['rubric_version']=v['version'];d['schema_freeze_id']=v['freeze_id']
    for c in d['canonical_concepts']:c['normalization_version']=v['version']
    if 'semantic_self_audit' not in d:
        d['semantic_self_audit']={'status':'AI_SELF_AUDIT_COMPLETED',
          'notes':['All source sentences reviewed in curated first pass.',
                   'Q1/Q2/Q3 schema decisions applied; repeated triples counted separately from source assertions.',
                   'D001 room-temperature scope and D010 best/proposed mechanism audited in Q1_FOLLOWUP_AUDIT.md.'],
          'human_validation':'NOT_REVIEWED'}
    p=BASE/'annotations/drafts'/f'{d["document_code"]}.jsonl'
    temp=p.with_suffix('.freeze.tmp');temp.write_text(json.dumps(d,ensure_ascii=False)+'\n',encoding='utf-8');temp.replace(p)
path.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
digest=hashlib.sha256(path.read_bytes()).hexdigest()
report={'freeze_id':v['freeze_id'],'rubric_version':v['version'],'relation_count':18,
        'vocabulary_sha256':digest,'annotation_schema_sha256':hashlib.sha256((BASE/'annotation.schema.json').read_bytes()).hexdigest(),
        'dev_documents':[d['document_code'] for d in drafts],'used_relation_types':dict(used),
        'proposed_or_domain_extension_types':dict(proposed),
        'unresolved_dev_questions':sum(len(d['unresolved']) for d in drafts),
        'new_types_admitted_from_proposals':[],
        'policy':'Evaluation splits use exactly this schema. Gaps are recorded, not used to modify it.',
        'human_gold_approval':False}
(BASE/'annotations/reports/DEV_ONTOLOGY_FREEZE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Frozen',len(drafts),'DEV documents;',len(used),'used types;',report['unresolved_dev_questions'],'unresolved questions.')
