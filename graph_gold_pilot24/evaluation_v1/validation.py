"""Explicit evaluation metadata adapter around the immutable DEV-v1 validator."""
import copy
import hashlib
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import validate_ontology_v1 as frozen
from jsonschema import Draft202012Validator, FormatChecker

ENVELOPE = 'pilot24-evaluation-envelope-1.0'
BASIS = 'AI_FROZEN_ONTOLOGY_SOURCE_REVIEW'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_approval():
    errors = frozen.validate_spec() + frozen.check_freeze()
    approval = json.loads((BASE/'ontology/approvals/pilot24-ontology-v1.0.json').read_text(encoding='utf-8'))
    for name, path in [('ontology_sha256', frozen.SPEC/'ontology.json'),
                       ('schema_sha256', frozen.SPEC/'annotation.schema.json'),
                       ('freeze_manifest_sha256', frozen.SPEC/'FREEZE_MANIFEST.json')]:
        if approval[name] != digest(path): errors.append('Approval hash mismatch: '+name)
    if approval['status'] != 'HUMAN_APPROVED_FOR_PILOT_V1': errors.append('Schema approval missing')
    if approval['individual_annotation_approval'] or approval['gold_dataset_approval']:
        errors.append('Schema approval incorrectly includes annotations')
    current=json.loads((BASE/'ontology/CURRENT_STATUS.json').read_text(encoding='utf-8'))
    adapter=json.loads((BASE/'annotations/reviews/relation_vocabulary.json').read_text(encoding='utf-8'))
    if current['status']!=approval['status'] or adapter['status']!=approval['status']:
        errors.append('Effective schema approval status mismatch')
    if adapter['relations']!=frozen.load_spec()['relations']:
        errors.append('Current vocabulary adapter changed frozen definitions')
    return errors


def schema_overlay():
    schema = json.loads((frozen.SPEC/'annotation.schema.json').read_text(encoding='utf-8'))
    schema['title'] = 'Evaluation metadata envelope; immutable ontology v1.0 constraints'
    context = schema['properties']['assertions']['items']['properties']['source_context']
    context['properties']['interpretation_basis'] = {'const': BASIS}
    schema['properties']['evaluation_envelope_version'] = {'const': ENVELOPE}
    schema['properties']['annotation_provenance'] = {'type': 'object',
        'required': ['actor', 'source_split', 'ontology_approval_ref', 'label_human_review', 'ontology_changed'],
        'properties': {'actor': {'const': 'AI'}, 'source_split': {'enum': ['CALIBRATION','HOLDOUT']},
            'ontology_approval_ref': {'const': 'USER-ONTOLOGY-V1-APPROVAL-20261021'},
            'label_human_review': {'const': 'NOT_REVIEWED'}, 'ontology_changed': {'const': False}}}
    schema['required'] += ['evaluation_envelope_version','annotation_provenance']
    return schema


def validate(d, source):
    audit_errors=[]
    spans={e['span_id']:e for e in d.get('evidence_spans',[])}
    chunks={c['chunk_id']:c for c in source['chunks']}
    for case in d.get('audit_abstentions',[]):
        if case.get('status')!='UNRESOLVED':audit_errors.append('Audit abstention status drift')
        if not case.get('evidence'):audit_errors.append('Audit abstention evidence missing')
        for e in case.get('evidence',[]):
            chunk=chunks.get(e.get('chunk_id'))
            if not chunk or e!=spans.get(e.get('span_id')) or chunk['text'][e['start']:e['end']]!=e['text']:
                audit_errors.append('Audit abstention source evidence mismatch')
    if d.get('split') == 'DEV':
        return frozen.validate(d, source)+audit_errors
    errors = check_approval()+audit_errors
    if d.get('split') not in ('CALIBRATION','HOLDOUT') or d.get('split') != source.get('split'):
        return errors + ['Evaluation source/split identity mismatch']
    schema = Draft202012Validator(schema_overlay(), format_checker=FormatChecker())
    errors += ['Evaluation envelope: '+'.'.join(map(str,e.absolute_path))+': '+e.message for e in schema.iter_errors(d)]
    provenance = d.get('annotation_provenance', {})
    if provenance.get('source_split') != d['split']: errors.append('Actual annotation provenance split mismatch')
    if d.get('review', {}).get('ontology_human_approval') is not True:
        errors.append('Evaluation annotation must reference the approved schema')
    projected = copy.deepcopy(d)
    projected['split'] = 'DEV'
    source_projection = copy.deepcopy(source)
    source_projection['split'] = 'DEV'
    for a in projected.get('assertions', []):
        a.setdefault('source_context', {})['interpretation_basis'] = 'AI_DEV_SOURCE_REVIEW'
    # Only envelope metadata is projected; all semantic/source constraints stay intact.
    try:
        errors += frozen.validate(projected, source_projection)
    except (KeyError, TypeError, ValueError) as error:
        errors.append('Malformed annotation rejected: '+str(error))
    return errors
