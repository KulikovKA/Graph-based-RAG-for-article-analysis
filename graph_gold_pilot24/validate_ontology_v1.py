"""DEV-only ontology-v1 validation; structural validity is not semantic truth.

Evaluation-split inputs are intentionally not loaded by this entrypoint.
"""
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator,FormatChecker

BASE=Path(__file__).resolve().parent
SPEC=BASE/'ontology/v1.0'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load_spec():
    return json.loads((SPEC/'ontology.json').read_text(encoding='utf-8'))


def validate_spec():
    spec=load_spec();errors=[]
    if spec.get('ontology_id')!='pilot24-ontology-v1.0':errors.append('Ontology identity invalid')
    if spec.get('status')!='TECHNICALLY_FROZEN_PENDING_HUMAN_APPROVAL':errors.append('Ontology status invalid')
    if len(spec.get('entities',{}))!=12:errors.append('Expected the 12 existing entity kinds')
    entity_kinds=set(spec.get('entities',{}))
    keys=['definition','direction','head_kinds','tail_kinds','required_qualifiers','optional_qualifiers',
          'supported_polarities','supported_modalities','positive_example','contrast','nearest_relations','ambiguity_policy','group_policy']
    for name,rule in spec.get('relations',{}).items():
        for k in keys:
            if k not in rule:errors.append(name+' missing '+k)
        for field in ('head_kinds','tail_kinds'):
            if not rule.get(field) or not set(rule[field])<=entity_kinds:errors.append(name+' invalid '+field)
        for k in ('definition','direction','contrast','nearest_relations','ambiguity_policy','group_policy'):
            if not rule.get(k):errors.append(name+' empty '+k)
    raw=(SPEC/'ontology.json').read_text(encoding='utf-8')
    if '????' in raw or '\ufffd' in raw:errors.append('Damaged encoding in ontology')
    schema_path=SPEC/'ontology.schema.json'
    if schema_path.exists():
        schema=Draft202012Validator(json.loads(schema_path.read_text(encoding='utf-8')))
        errors += ['Ontology JSON Schema: '+e.message for e in schema.iter_errors(spec)]
    return errors


def required_types(rule):
    result=[]
    for q in rule.get('required_qualifiers',[]):
        result.append(q if isinstance(q,str) else q.get('qualifier_type',q.get('name')))
    return result


def qualifier_schema(spec,name):
    definitions=spec.get('qualifiers',{})
    if 'types' in definitions:definitions=definitions['types']
    if not isinstance(definitions,dict):return None
    return definitions.get(name)


def check_freeze():
    path=SPEC/'FREEZE_MANIFEST.json'
    if not path.is_file():return ['Technical freeze manifest absent']
    manifest=json.loads(path.read_text(encoding='utf-8'));errors=[]
    if manifest.get('ontology_id')!='pilot24-ontology-v1.0':errors.append('Unexpected manifest ontology identity')
    if manifest.get('status')!='TECHNICALLY_FROZEN_PENDING_HUMAN_APPROVAL':errors.append('Unexpected freeze status')
    required_artifacts={'ontology.json','annotation.schema.json','ontology.schema.json',
        'adjudication_decisions.jsonl','ANNOTATION_RUBRIC.md','RELATION_DEFINITIONS.md','ENTITY_DEFINITIONS.md'}
    if not required_artifacts<=set(manifest.get('artifact_sha256',{})):errors.append('Incomplete frozen artifact identity')
    commit=manifest.get('content_commit_sha','')
    if len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):errors.append('Content commit identity invalid')
    states=manifest.get('approval_states',{})
    if states.get('final_human_ontology_approval',{}).get('status')!='PENDING':errors.append('Human ontology approval state is not pending')
    if states.get('gold_labels',{}).get('human_review')!='NOT_REVIEWED':errors.append('Unrecorded human label approval')
    for name,expected in manifest.get('artifact_sha256',{}).items():
        p=(SPEC/name).resolve()
        if not p.is_relative_to(SPEC.resolve()) or not p.is_file() or sha(p)!=expected:
            errors.append('Frozen artifact hash mismatch: '+name)
    for name,expected in manifest.get('tooling_sha256',{}).items():
        p=(BASE/name).resolve()
        if not p.is_relative_to(BASE.resolve()) or not p.is_file() or sha(p)!=expected:errors.append('Frozen tooling hash mismatch: '+name)
    if manifest.get('ontology_sha256')!=sha(SPEC/'ontology.json'):errors.append('Ontology hash mismatch')
    if manifest.get('schema_sha256')!=sha(SPEC/'annotation.schema.json'):errors.append('Schema hash mismatch')
    return errors


def validate(d,source,template=None,vocabulary=None,*,require_freeze=True):
    spec=load_spec();errors=[]
    if spec.get('approval',{}).get('final_human_ontology_approved') is not False:errors.append('Final human ontology approval must remain false pending the user decision')
    if d.get('split')!='DEV' or source.get('split')!='DEV':
        return ['Ontology-v1 design validation accepts DEV only; evaluation data are not loaded']
    schema=Draft202012Validator(json.loads((SPEC/'annotation.schema.json').read_text(encoding='utf-8')),format_checker=FormatChecker())
    errors += ['JSON Schema: '+'.'.join(map(str,e.absolute_path))+': '+e.message for e in schema.iter_errors(d)]
    # Shared grounding checks are parameterized, never fed evaluation rows.
    from validate_annotations import validate_legacy
    if template is None:
        template=dict(schema_version='graph-gold-pilot-v0',document_code=d['document_code'],
            document_id=source['document_id'],revision_id=source['revision_id'],split='DEV',
            annotation_status='',annotation_scope='',exhaustive_entities=False,exhaustive_relations=False,
            mentions=[],assertions=[],identity_decisions=[],unresolved=[],review={})
    adapter={'version':spec['ontology_id'],'relations':spec['relations']}
    errors += validate_legacy(d,source,template,adapter,enforce_legacy_approval=False)
    def check(ok,message):
        if not ok:errors.append(message)
    check(d.get('ontology_id')==spec['ontology_id'],'Ontology version identity mismatch')
    check(d.get('ontology_version')=='1.0','Ontology version mismatch')
    check(d.get('schema_freeze_id')==spec['ontology_id'],'Freeze identity mismatch')
    check(d.get('ontology_hash')==sha(SPEC/'ontology.json'),'Draft ontology hash mismatch')
    check(d.get('rubric_version')==spec['ontology_id'],'Rubric identity mismatch')
    spans={s['span_id']:s for s in d.get('evidence_spans',[])}
    mentions={m['mention_id']:m for m in d.get('mentions',[])}
    for mention in mentions.values():
        if mention.get('contextual_role') in ('electronic_charge_region','electronic_interface'):
            check(mention.get('kind')=='MORPHOLOGY','Electronic charge/interface structures must be MORPHOLOGY')
    for a in d.get('assertions',[]):
        rule=spec['relations'].get(a['relation_type'])
        if rule is None:continue
        check(a['polarity'] in rule.get('supported_polarities',['POSITIVE','NEGATIVE','UNKNOWN']),'Unsupported predicate polarity')
        check(a['modality'] in rule.get('supported_modalities',['ASSERTED','PROPOSED','COMPARED','HYPOTHETICAL','UNKNOWN']),'Unsupported predicate modality')
        names=[q['qualifier_type'] for q in a['qualifiers']]
        for required in required_types(rule):check(required in names,'Required qualifier missing: '+str(required))
        allowed_names=set(required_types(rule))|set(rule.get('optional_qualifiers',[]))
        check(set(names)<=allowed_names,'Qualifier not permitted for predicate: '+a['relation_type'])
        h,t=mentions.get(a['head_mention_id']),mentions.get(a['tail_mention_id'])
        if h and t:
            if rule.get('endpoint_pairs'):check([h['kind'],t['kind']] in rule['endpoint_pairs'],'Invalid predicate endpoint pair')
            if rule.get('head_contextual_roles'):check(h['contextual_role'] in rule['head_contextual_roles'],'Required head contextual role missing')
            if rule.get('tail_contextual_roles'):check(t['contextual_role'] in rule['tail_contextual_roles'],'Required tail contextual role missing')
            if a['relation_type']=='HAS_MEMBER' and h['kind']!=t['kind']:
                check(h['kind']=='PROPERTY' and t['kind']=='PERFORMANCE' and h['contextual_role']=='requirement_bundle','Invalid mixed-kind membership')
        context=a.get('source_context',{})
        check(context.get('source_modality')==a['modality'],'Modality drift from recorded AI source interpretation')
        check(context.get('source_polarity')==a['polarity'],'Negation drift from recorded AI source interpretation')
        check(context.get('source_relation_type')==a['relation_type'],'Predicate drift from recorded AI source interpretation')
        check(set(context.get('evidence_span_ids',[]))=={e['span_id'] for e in a['evidence']},'Source-context evidence mismatch')
        check(context.get('interpretation_basis')=='AI_DEV_SOURCE_REVIEW','Source interpretation provenance missing')
        check(a.get('support_kind')=='DIRECT_SOURCE','Direct-source support required; no implicit transitive facts')
        for q in a['qualifiers']:
            definition=qualifier_schema(spec,q['qualifier_type'])
            check(definition is not None,'Unknown controlled qualifier type: '+q['qualifier_type'])
            if isinstance(definition,dict):
                allowed=definition.get('allowed_values',definition.get('enum'))
                if allowed is not None:check(q['raw_value'] in allowed,'Invalid controlled qualifier value: '+q['qualifier_type'])
                value_schema=definition.get('value_schema')
                if value_schema:
                    check(not list(Draft202012Validator(value_schema).iter_errors(q['raw_value'])),'Qualifier value-schema mismatch: '+q['qualifier_type'])
                value=q['raw_value']
                actual_type='number' if type(value) in (int,float) else 'array' if isinstance(value,list) else 'string' if isinstance(value,str) else 'null' if value is None else 'boolean' if isinstance(value,bool) else 'object'
                if definition.get('raw_value_types'):check(actual_type in definition['raw_value_types'],'Qualifier value type mismatch: '+q['qualifier_type'])
            requirements=rule.get('required_qualifiers',{})
            if isinstance(requirements,dict) and isinstance(requirements.get(q['qualifier_type']),dict):
                constraints=requirements[q['qualifier_type']]
                if 'enum' in constraints:check(q['raw_value'] in constraints['enum'],'Predicate-specific qualifier value mismatch: '+q['qualifier_type'])
        if a['relation_type']=='MEETS_REQUIREMENT':
            values={q['qualifier_type']:q['raw_value'] for q in a['qualifiers']}
            if values.get('joint_requirement')=='all':
                members={x['tail_mention_id'] for x in d['assertions'] if x['relation_type']=='HAS_MEMBER' and x['head_mention_id']==a['tail_mention_id'] and x['polarity']=='POSITIVE'}
                check(len(members)>=2,'Joint requirement must retain a group with at least two explicit members')
    if require_freeze:errors += check_freeze()
    return errors


def run(paths=None,*,require_freeze=True):
    spec_errors=validate_spec()
    if spec_errors:
        print(json.dumps({'ontology_errors':spec_errors},ensure_ascii=False));return 1
    sources={json.loads(line)['document_code']:json.loads(line) for line in (SPEC/'dev_sources.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()}
    assert len(sources)==12 and all(s['split']=='DEV' for s in sources.values())
    paths=paths or sorted((SPEC/'dev_drafts').glob('*.jsonl'))
    reports=[]
    for p in paths:
        if p.stem not in sources:
            raise ValueError('Refusing non-DEV or unknown input path before opening it: '+str(p))
        for line in p.read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            d=json.loads(line)
            if d.get('document_code')!=p.stem:raise ValueError('Draft filename/document identity mismatch: '+str(p))
            errors=validate(d,sources[d['document_code']],require_freeze=require_freeze)
            reports.append(dict(document_code=d['document_code'],status='FAIL' if errors else 'PASS',
                errors=errors,mentions=len(d['mentions']),assertions=len(d['assertions']),
                unresolved=len(d['unresolved']),human_review='NOT_REVIEWED',
                semantic_truth='NOT_ESTABLISHED_BY_STRUCTURAL_VALIDATION'))
    target=SPEC/'validation_report.json'
    target.write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'documents':len(reports),'passed':sum(r['status']=='PASS' for r in reports),'errors':{r['document_code']:r['errors'] for r in reports if r['errors']}},ensure_ascii=False))
    return 0 if len(reports)==12 and all(r['status']=='PASS' for r in reports) else 1


if __name__=='__main__':raise SystemExit(run())
