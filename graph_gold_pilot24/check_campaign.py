"""Grounding regression checks; not independent human semantic validation."""
import copy
import hashlib
import json
import zipfile
from campaign_paths import BASE,draft_paths,private_root
from validate_annotations import read_jsonl,validate


def main():
    sources={d['document_code']:d for d in read_jsonl(BASE/'pilot24_sources.jsonl')}
    templates={d['document_code']:d for d in read_jsonl(BASE/'gold_annotation_template.jsonl')}
    drafts={read_jsonl(p)[0]['document_code']:read_jsonl(p)[0] for p in draft_paths()}
    v=json.loads((BASE/'annotations/reviews/relation_vocabulary.json').read_text(encoding='utf-8'))
    assert len(drafts)==24 and len(v['relations'])==18 and v['frozen']
    for code,d in drafts.items():
        assert not validate(d,sources[code],templates[code],v)
        assert d['review']['primary_annotator'] is None and d['review']['secondary_annotator'] is None
        assert d['review']['human_review_status']=='NOT_REVIEWED'
    source=drafts['D003'];checks={}
    def reject(name,mutate):
        d=copy.deepcopy(source);mutate(d)
        errors=validate(d,sources['D003'],templates['D003'],v)
        assert errors,name
        checks[name]={'status':'REJECTED_AS_EXPECTED','errors_detected':len(errors)}
    reject('wrong_unicode_offset',lambda d:d['mentions'][0].update(start=d['mentions'][0]['start']+1))
    reject('nonexistent_endpoint',lambda d:d['assertions'][0].update(head_mention_id='00000000-0000-0000-0000-000000000000'))
    reject('unapproved_predicate',lambda d:d['assertions'][0].update(relation_type='CAUSES'))
    reject('invalid_polarity',lambda d:d['assertions'][0].update(polarity='AFFIRMATIVE'))
    reject('fabricated_human_review',lambda d:d['review'].update(human_review_status='APPROVED'))
    reject('incomplete_sentence_coverage',lambda d:d['sentence_review'].pop())
    def attachment(d):
        next(a for a in d['assertions'] if a['qualifiers'])['qualifiers'][0]['applies_to_assertion_id']='00000000-0000-0000-0000-000000000000'
    reject('wrong_qualifier_attachment',attachment)
    d=drafts['D001'];ms={m['mention_id']:m for m in d['mentions']}
    wash=next(a for a in d['assertions'] if ms[a['tail_mention_id']]['local_key']=='wash')
    assert not any(q['qualifier_type']=='temperature' for q in wash['qualifiers'])
    assert sum(a['relation_type']=='IMPROVES' for a in d['assertions'])==1
    d=drafts['D010'];ms={m['mention_id']:m for m in d['mentions']}
    for k,role in [('junction','electronic_interface'),('acc','electronic_charge_region'),('dep','electronic_charge_region')]:
        m=next(m for m in ms.values() if m['local_key']==k);assert m['kind']=='MORPHOLOGY' and m['contextual_role']==role
    s7=next(s['span_id'] for s in d['sentence_review'] if s['sentence_id']=='S7')
    assert all(a['modality']=='PROPOSED' for a in d['assertions'] if any(e['span_id']==s7 for e in a['evidence']))
    best=next(a for a in d['assertions'] if ms[a['tail_mention_id']]['local_key']=='best')
    assert not best['qualifiers'] and best['modality']=='COMPARED'
    assert any(a['relation_type']=='OPTIMIZES' for a in drafts['D003']['assertions'])
    assert sum(a['relation_type']=='FACILITATES' for a in drafts['D004']['assertions'])==2
    integrity=json.loads((BASE/'annotations/reports/source_integrity.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((BASE/'pilot24_sources.jsonl').read_bytes()).hexdigest()==integrity['source_output_sha256']
    with zipfile.ZipFile(BASE.parent/'graph_gold_pilot24_preparation.zip') as z:
        for item in z.infolist():assert (BASE.parent/item.filename).read_bytes()==z.read(item)
    assert not list((BASE/'annotations/gold').iterdir())
    assert len(list((BASE/'annotations/drafts').glob('*.jsonl')))==18
    assert len(list((private_root()/'drafts').glob('*.jsonl')))==6
    report={'rubric_version':v['version'],'validated_documents':24,'json_schema_and_source_checks':'PASS',
            'negative_validation_cases':checks,'Q1_Q2_Q3_regressions':'PASS',
            'sources_and_original_package_unchanged':True,'private_holdout_separation':'PASS',
            'human_reviewed':0,'approved_gold':0,
            'scope':'Structural negative tests and preservation of recorded decisions; not independent semantic validation.'}
    (BASE/'annotations/reports/validator_checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('PASS: 24 drafts; 7 negative validation cases; Q1/Q2/Q3 preserved; HOLDOUT private.')


if __name__=='__main__':main()
