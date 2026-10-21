"""Promote unchanged AI labels after the owner's explicit manual-review attestation."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASE=Path(__file__).resolve().parents[1]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'evaluation_v1'))
import validation as evaluation
from campaign_paths import draft_path,private_root
from jsonschema import Draft202012Validator,FormatChecker

RELEASE_ID='pilot24-owner-reviewed-gold-v1-20261021'
DECISION_ID='OWNER-MANUAL-REVIEW-24-20261021'
STANDARD='HUMAN_REVIEWED_GOLD_STANDARD'
BASELINE_COMMIT='83981942ed5b8a9a1e46e1440d05d98ff50fd438'
TOP_METADATA=('annotation_status','review','review_provenance','data_standard','evaluation_status','review_envelope_version')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


def write_jsonl(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),encoding='utf-8',newline='\n')


def private_release():
    root=private_root()/'owner_review_v1'
    assert not root.resolve().is_relative_to(BASE.parent.resolve())
    return root


def artifact_root(split):return private_release() if split=='HOLDOUT' else OUT


def gold_path(code,split):
    folder=private_root()/'gold' if split=='HOLDOUT' else BASE/'annotations/gold'
    return folder/(code+'.jsonl')


def sources():
    return [json.loads(line) for line in (BASE/'pilot24_sources.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]


def owner_decision():return json.loads((OUT/'OWNER_DECISION.json').read_text(encoding='utf-8'))


def baseline(d):
    return json.loads((artifact_root(d['split'])/'ai_baseline'/f"{d['document_code']}.jsonl").read_text(encoding='utf-8'))


def ai_projection(d,before):
    """Restore only authorized review metadata; equality checks every other field."""
    result=copy.deepcopy(d)
    for field in TOP_METADATA:
        if field in before:result[field]=copy.deepcopy(before[field])
        else:result.pop(field,None)
    if 'annotation_provenance' in before:
        result['annotation_provenance']['label_human_review']=before['annotation_provenance']['label_human_review']
    for field,id_key in [('mentions','mention_id'),('assertions','assertion_id'),('identity_decisions','decision_id')]:
        old={x[id_key]:x for x in before[field]}
        for item in result[field]:
            original=old.get(item[id_key],{})
            for key in ['annotation_status','human_review_status']:
                if key in original:item[key]=original[key]
                else:item.pop(key,None)
    return result


def gold_schema(split):
    schema=json.loads((evaluation.frozen.SPEC/'annotation.schema.json').read_text(encoding='utf-8')) if split=='DEV' else evaluation.schema_overlay()
    schema['title']='Owner-reviewed Gold metadata envelope; ontology v1.0 unchanged'
    schema['properties']['annotation_status']={'const':'HUMAN_REVIEWED'}
    review=schema['properties']['review']
    review['properties'].update(primary_annotator={'const':'project_owner'},secondary_annotator={'const':None},human_review_status={'const':'APPROVED'},review_date={'const':'2026-10-21'},review_method={'const':'manual_owner_review'},owner_decision_ref={'const':DECISION_ID})
    review['required']+=['review_date','review_method','owner_decision_ref']
    for field in ['mentions','assertions','identity_decisions']:
        item=schema['properties'][field]['items']
        item['properties']['annotation_status']={'const':'HUMAN_REVIEWED'}
        if 'annotation_status' not in item['required']:item['required'].append('annotation_status')
    identity=schema['properties']['identity_decisions']['items']
    identity['properties']['human_review_status']={'const':'APPROVED'}
    identity['required'].append('human_review_status')
    if split!='DEV':
        schema['properties']['annotation_provenance']['properties']['label_human_review']={'const':'APPROVED'}
    schema['properties'].update(data_standard={'const':STANDARD},evaluation_status={'const':'OWNER_APPROVED_FOR_EVALUATION'},review_envelope_version={'const':'pilot24-owner-review-envelope-1.0'},review_provenance={'type':'object','required':['decision_id','confirmation_source','independent_secondary_review','origin'], 'properties':{'decision_id':{'const':DECISION_ID},'confirmation_source':{'const':'USER_CHAT_ATTESTATION'},'independent_secondary_review':{'const':False},'origin':{'const':'AI_GENERATED'}}})
    schema['required']+=['data_standard','evaluation_status','review_envelope_version','review_provenance']
    return schema


def validate_gold(d,source):
    errors=evaluation.check_approval()
    decision=owner_decision()
    if decision['decision_id']!=DECISION_ID or decision['human_review_confirmed_by_owner'] is not True:
        errors.append('Owner manual-review confirmation missing')
    if d.get('document_code') not in {x['document_code'] for x in decision['documents']}:
        errors.append('Document absent from owner approval scope')
    if d.get('split')!=source.get('split'):return errors+['Gold source/split mismatch']
    schema=Draft202012Validator(gold_schema(source['split']),format_checker=FormatChecker())
    errors+=['Gold metadata: '+'.'.join(map(str,e.absolute_path))+': '+e.message for e in schema.iter_errors(d)]
    try:
        before=baseline(d)
        projected=ai_projection(d,before)
        if projected!=before:errors.append('Approved annotation content changed beyond permitted review metadata')
        if d['unresolved']!=before['unresolved'] or d.get('audit_abstentions',[])!=before.get('audit_abstentions',[]):
            errors.append('Approved abstentions changed')
        errors+=evaluation.validate(projected,source)
    except (KeyError,TypeError,ValueError) as error:errors.append('Invalid Gold annotation: '+str(error))
    return errors


def promote():
    assert not evaluation.check_approval(),evaluation.check_approval()
    decision=owner_decision();ss=sources()
    assert len(ss)==24 and {s['document_code'] for s in ss}=={d['document_code'] for d in decision['documents']}
    count=0
    for source in ss:
        code,split=source['document_code'],source['split'];root=artifact_root(split)
        origin=draft_path(code,split);snapshot=root/'ai_baseline'/(code+'.jsonl')
        snapshot.parent.mkdir(parents=True,exist_ok=True)
        if snapshot.exists():assert snapshot.read_bytes()==origin.read_bytes(),'AI origin changed'
        else:snapshot.write_bytes(origin.read_bytes())
        before=json.loads(snapshot.read_text(encoding='utf-8'));d=copy.deepcopy(before)
        d.update(annotation_status='HUMAN_REVIEWED',data_standard=STANDARD,evaluation_status='OWNER_APPROVED_FOR_EVALUATION',review_envelope_version='pilot24-owner-review-envelope-1.0')
        d['review'].update(primary_annotator='project_owner',secondary_annotator=None,human_review_status='APPROVED',review_date='2026-10-21',review_method='manual_owner_review',owner_decision_ref=DECISION_ID,adjudication_status='OWNER_MANUAL_REVIEW_CONFIRMED_IN_CHAT')
        d['review_provenance']=dict(decision_id=DECISION_ID,confirmation_source='USER_CHAT_ATTESTATION',independent_secondary_review=False,origin='AI_GENERATED',approval_scope='ALL_24_CURRENT_DOCUMENT_ANNOTATIONS_ABSTENTIONS_PRESERVED')
        if 'annotation_provenance' in d:d['annotation_provenance']['label_human_review']='APPROVED'
        for field in ['mentions','assertions','identity_decisions']:
            for item in d[field]:
                item['annotation_status']='HUMAN_REVIEWED'
                if field=='identity_decisions':item['human_review_status']='APPROVED'
        assert ai_projection(d,before)==before
        errors=validate_gold(d,source)
        if errors:raise ValueError((code,errors))
        target=gold_path(code,split);write_jsonl(target,[d])
        changed=[k for k in d if d.get(k)!=before.get(k)]
        patch=[dict(op='replace' if k in before else 'add',path='/'+k,value=d[k]) for k in changed]
        write_jsonl(root/'review_metadata_patches'/(code+'.jsonl'),[dict(document_code=code,baseline_sha256=digest(snapshot),gold_sha256=digest(target),patch=patch)])
        count+=len(d['unresolved'])+len(d.get('audit_abstentions',[]))
    assert count==23
    public_log=BASE/'annotations/reviews/adjudication_decisions.jsonl'
    records=[json.loads(l) for l in public_log.read_text(encoding='utf-8').splitlines() if l.strip()]
    if not any(r['decision_id']==DECISION_ID for r in records):
        record=dict(decision_id=DECISION_ID,actor='project_owner',decision='CONFIRM_MANUAL_OWNER_REVIEW_AND_APPROVE_ALL_24',confirmation_source='USER_CHAT_ATTESTATION',user_statement=decision['user_statement'],annotation_status='HUMAN_REVIEWED',human_review_status='APPROVED',primary_annotator='project_owner',secondary_annotator=None,review_date='2026-10-21',review_method='manual_owner_review',documents=decision['documents'],abstentions_preserved=23,ontology_changed=False)
        with public_log.open('ab') as output:output.write((json.dumps(record,ensure_ascii=False)+'\n').encode('utf-8'))
    state=dict(dataset_id=RELEASE_ID,annotation_status='HUMAN_REVIEWED',human_review_status='APPROVED',data_standard=STANDARD,evaluation_status='OWNER_APPROVED_FOR_EVALUATION',primary_annotator='project_owner',secondary_annotator=None,review_date='2026-10-21',review_method='manual_owner_review',independent_secondary_review=False,owner_decision_ref=DECISION_ID,ontology_id='pilot24-ontology-v1.0',documents=24,public_gold_documents=18,private_holdout_gold_documents=6,abstentions=23,public_gold_path='annotations/gold/',holdout_gold_storage='Closed local storage outside repository',report='owner_review_v1/REPORT.md',annotation_origin='AI_GENERATED',previous_ai_release_commit=BASELINE_COMMIT)
    dump(BASE/'annotations/CURRENT_DATASET.json',state)
    for split in ['DEV','CALIBRATION','HOLDOUT']:dump(OUT/f'owner_review_{split.lower()}.schema.json',gold_schema(split))
    print('Promoted 24 owner-reviewed documents; 18 public Gold files, 6 private; 23 abstentions unchanged.')


def check_predecessor():
    """Old release hashes refer to its historical commit, not new review tools."""
    manifest=json.loads((BASE/'evaluation_v1/RELEASE_MANIFEST.json').read_text(encoding='utf-8'))
    for name,expected in manifest['public_artifact_sha256'].items():
        blob=subprocess.check_output(['git','show',BASELINE_COMMIT+':graph_gold_pilot24/'+name],cwd=BASE.parent)
        assert hashlib.sha256(blob).hexdigest()==expected,'Historical AI release hash mismatch: '+name
    return True


def validate_all():
    assert not evaluation.check_approval(),evaluation.check_approval()
    rows=[];private_details=[]
    for source in sources():
        code,split=source['document_code'],source['split'];p=gold_path(code,split)
        d=json.loads(p.read_text(encoding='utf-8'));errors=validate_gold(d,source)
        ms={m['mention_id']:m for m in d['mentions']}
        triples={(ms[a['head_mention_id']]['canonical_concept'],a['relation_type'],ms[a['tail_mention_id']]['canonical_concept']) for a in d['assertions']}
        patch_record=json.loads((artifact_root(split)/'review_metadata_patches'/(code+'.jsonl')).read_text(encoding='utf-8'))
        before=baseline(d);replay=copy.deepcopy(before)
        for op in patch_record['patch']:replay[op['path'][1:]]=op['value']
        assert replay==d and patch_record['gold_sha256']==digest(p)
        row=dict(document_code=code,split=split,annotation_status=d['annotation_status'],human_review_status=d['review']['human_review_status'],primary_annotator=d['review']['primary_annotator'],secondary_annotator=d['review']['secondary_annotator'],review_date=d['review']['review_date'],review_method=d['review']['review_method'],mentions=len(d['mentions']),assertions=len(d['assertions']),unique_canonical_triples=len(triples),abstentions=len(d['unresolved'])+len(d.get('audit_abstentions',[])),validation='FAIL' if errors else 'PASS',content_unchanged=ai_projection(d,before)==before)
        if split=='HOLDOUT':private_details.append(dict(metrics=row,errors=errors,annotation_sha256=digest(p)))
        elif errors:row['errors']=errors
        rows.append(row)
    assert sum(r['abstentions'] for r in rows)==23
    totals={key:sum(r[key] for r in rows) for key in ['mentions','assertions','unique_canonical_triples','abstentions']}
    report=dict(dataset_id=RELEASE_ID,ontology_id='pilot24-ontology-v1.0',ontology_sha256=digest(evaluation.frozen.SPEC/'ontology.json'),ontology_schema_sha256=digest(evaluation.frozen.SPEC/'annotation.schema.json'),data_standard=STANDARD,annotation_origin='AI_GENERATED',evaluation_status='OWNER_APPROVED_FOR_EVALUATION',human_review_status='APPROVED',annotation_status='HUMAN_REVIEWED',primary_annotator='project_owner',secondary_annotator=None,review_date='2026-10-21',review_method='manual_owner_review',confirmation_source='USER_CHAT_ATTESTATION',independent_secondary_review=False,inter_annotator_agreement=None,human_reviewed_documents=sum(r['annotation_status']=='HUMAN_REVIEWED' for r in rows),gold_documents=24,public_gold_documents=18,private_holdout_gold_documents=6,structural_pass=sum(r['validation']=='PASS' for r in rows),totals=totals,documents=rows,limitations=['Single project-owner manual review, confirmed by the owner in chat; no independent second annotator or inter-annotator agreement.','Structural PASS verifies format, source grounding and unchanged content; it does not measure semantic recall.','Abstentions remain unresolved and are excluded from scored positive/negative labels.'],experiments_started=False)
    dump(OUT/'REPORT.json',report);dump(BASE/'annotations/reports/HUMAN_REVIEW_STATUS.json',report)
    dump(private_release()/'validation_details.json',private_details)
    lines=['# Owner-reviewed Gold Dataset — pilot24','',
        'All 24 documents are **HUMAN_REVIEWED**, with **human_review_status=APPROVED**, on the project owner\'s explicit confirmation of personal manual review in chat. Review date: **2026-10-21**. Primary annotator: **project_owner**; secondary annotator: **null**; method: **manual_owner_review**.','',
        'Standard: **HUMAN_REVIEWED_GOLD_STANDARD**; origin: **AI_GENERATED**; evaluation status: **OWNER_APPROVED_FOR_EVALUATION**. This is a single-owner review, not independent double annotation. Inter-annotator agreement is not measured.','',
        '| Document | Split | Mentions | Assertions | Unique triples | Abstentions | Annotation status | Check |','|---|---|---:|---:|---:|---:|---|---|']
    for r in rows:lines.append(f"| {r['document_code']} | {r['split']} | {r['mentions']} | {r['assertions']} | {r['unique_canonical_triples']} | {r['abstentions']} | {r['annotation_status']} | {r['validation']} |")
    lines+=['',f"Totals: **{totals['mentions']} mentions, {totals['assertions']} assertions, {totals['unique_canonical_triples']} unique canonical triples, {totals['abstentions']} abstentions**. Structural result: **{report['structural_pass']}/24 PASS**.",'',
        'Every source span, evidence item, relation, qualifier, modality, polarity, canonical identity and all 23 abstention objects are identical to the approved AI baseline after projecting only explicit review metadata. Original AI drafts and prior release manifests remain historical. Nested annotations are marked HUMAN_REVIEWED; historical abstention decision records are preserved exactly.','',
        'The immutable Ontology v1.0 and its technical-freeze hashes are unchanged. Separate owner-review metadata schemas permit human approval without modifying semantic ontology constraints. No A/B/F/C/D experiments were started.','',
        'Eighteen DEV/CALIBRATION Gold files are in annotations/gold/. The six HOLDOUT Gold files, snapshots, review patches, individual hashes and validation details remain in closed local storage outside Git. Public HOLDOUT rows contain review metadata and counts only.','']
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
    print(json.dumps({'human_reviewed_documents':report['human_reviewed_documents'],'passed':report['structural_pass'],'totals':totals}))
    return 0 if report['structural_pass']==24 else 1


if __name__=='__main__':
    if '--promote' in sys.argv:promote()
    raise SystemExit(validate_all())
