"""Build v1 JSON Schemas from the preserved envelope and controlled DEV ontology.

No evaluation data are accessed. The envelope name is retained for compatibility;
ontology_id, ontology_version and hashes identify its new semantic constraints.
"""
import copy
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent


def write(name, value):
    (BASE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def main():
    ontology = json.loads((BASE / 'ontology.json').read_text(encoding='utf-8'))
    schema = json.loads((BASE.parent / 'baselines/pilot24-auto-freeze-0.3/annotation_0.3.schema.json').read_text(encoding='utf-8'))
    schema['title'] = 'Pilot24 annotation envelope constrained by ontology v1.0'
    props = schema['properties']
    for field, value in {'ontology_id': ontology['ontology_id'], 'ontology_version': '1.0',
                         'schema_freeze_id': ontology['ontology_id'], 'rubric_version': ontology['ontology_id']}.items():
        props[field] = {'const': value}
        if field not in schema['required']:
            schema['required'].append(field)
    props['ontology_hash'] = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
    schema['required'].append('ontology_hash')
    props['annotation_status'] = {'const': 'AI_DRAFT'}
    props['mentions']['items']['properties']['kind'] = {'enum': list(ontology['entities'])}
    props['mentions']['items']['properties']['start']['minimum'] = 0
    props['mentions']['items']['properties']['end']['minimum'] = 1
    props['mentions']['items']['properties']['evidence_span_ids']['minItems'] = 1
    assertion = props['assertions']['items']
    ap = assertion['properties']
    ap['relation_type'] = {'enum': list(ontology['relations'])}
    ap['polarity'] = {'enum': ['POSITIVE', 'NEGATIVE']}
    ap['modality'] = {'enum': ['ASSERTED', 'PROPOSED', 'COMPARED', 'HYPOTHETICAL']}
    ap['support_status'] = {'const': 'SUPPORTED'}
    ap['support_kind'] = {'const': 'DIRECT_SOURCE'}
    ap['evidence']['minItems'] = 1
    ap['source_context'] = {'type': 'object', 'properties': {
        'source_relation_type': {'enum': list(ontology['relations'])},
        'source_modality': copy.deepcopy(ap['modality']),
        'source_polarity': copy.deepcopy(ap['polarity']),
        'interpretation_basis': {'const': 'AI_DEV_SOURCE_REVIEW'},
        'evidence_span_ids': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                              'items': {'type': 'string', 'format': 'uuid'}}},
        'required': ['source_relation_type', 'source_modality', 'source_polarity',
                     'interpretation_basis', 'evidence_span_ids'], 'additionalProperties': False}
    assertion['required'] += ['support_kind', 'source_context']
    qualifier = ap['qualifiers']['items']
    qualifier['properties']['qualifier_type'] = {'enum': list(ontology['qualifiers'])}
    qualifier['properties']['evidence_refs']['minItems'] = 1
    qualifier['allOf'] = []
    for name, rule in ontology['qualifiers'].items():
        value_rule = {'type': rule['raw_value_types']}
        if rule.get('enum') is not None:
            value_rule['enum'] = rule['enum']
        qualifier['allOf'].append({'if': {'properties': {'qualifier_type': {'const': name}}},
                                   'then': {'properties': {'raw_value': value_rule}}})
    assertion['allOf'] = []
    for name, rule in ontology['relations'].items():
        required = rule['required_qualifiers']
        allowed = list(required) + rule['optional_qualifiers']
        constraints = [{'items': {'properties': {'qualifier_type': {'enum': allowed}}}}]
        for qname, qrule in required.items():
            constraints.append({'contains': {'type': 'object', 'properties': {
                'qualifier_type': {'const': qname}, 'raw_value': qrule},
                'required': ['qualifier_type', 'raw_value']}, 'minContains': 1})
        assertion['allOf'].append({'if': {'properties': {'relation_type': {'const': name}}},
                                    'then': {'properties': {'qualifiers': {'allOf': constraints}}}})
    write('annotation.schema.json', schema)

    nonempty = {'type': 'string', 'minLength': 1}
    kinds = {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': {'enum': list(ontology['entities'])}}
    relation_props = {k: nonempty for k in ['definition', 'direction', 'contrast', 'nearest_relations', 'ambiguity_policy', 'group_policy']}
    relation_props.update(head_kinds=kinds, tail_kinds=kinds,
        required_qualifiers={'type': 'object', 'propertyNames': {'enum': list(ontology['qualifiers'])}, 'additionalProperties': {'type': 'object'}},
        optional_qualifiers={'type': 'array', 'uniqueItems': True, 'items': {'enum': list(ontology['qualifiers'])}},
        supported_polarities={'type': 'array', 'minItems': 1, 'items': {'enum': ['POSITIVE', 'NEGATIVE']}},
        supported_modalities={'type': 'array', 'minItems': 1, 'items': {'enum': ['ASSERTED', 'PROPOSED', 'COMPARED', 'HYPOTHETICAL']}},
        positive_example={'type': 'object', 'required': ['document_code', 'assertion_id', 'head', 'tail', 'polarity', 'modality', 'evidence', 'qualifiers'],
            'properties': {'document_code': {'type': 'string', 'pattern': '^D[0-9]{3}$'},
                           'evidence': {'type': 'array', 'minItems': 1, 'items': copy.deepcopy(ap['evidence']['items'])}}})
    meta = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object',
        'required': ['ontology_id', 'version', 'status', 'approval', 'entities', 'relations', 'qualifiers',
                     'qualifier_schema', 'polarity', 'modality', 'support_policy', 'evidence_policy', 'canonicalization', 'group_policy', 'provenance'],
        'properties': {'ontology_id': {'const': 'pilot24-ontology-v1.0'}, 'version': {'const': '1.0'},
            'status': {'const': 'TECHNICALLY_FROZEN_PENDING_HUMAN_APPROVAL'},
            'approval': {'type': 'object', 'required': ['final_human_ontology_approved', 'annotation_human_review_status', 'human_gold_documents'],
                'properties': {'final_human_ontology_approved': {'const': False},
                               'annotation_human_review_status': {'const': 'NOT_REVIEWED'}, 'human_gold_documents': {'const': 0}}},
            'entities': {'type': 'object', 'required': list(ontology['entities']), 'additionalProperties': False,
                'properties': {k: {'type': 'object', 'required': ['definition', 'examples', 'boundary', 'canonicalization'],
                                  'properties': {f: nonempty for f in ['definition', 'examples', 'boundary', 'canonicalization']}} for k in ontology['entities']}},
            'relations': {'type': 'object', 'minProperties': 1,
                'additionalProperties': {'type': 'object', 'required': list(relation_props), 'properties': relation_props}},
            'qualifiers': {'type': 'object', 'minProperties': 1, 'additionalProperties': {'type': 'object',
                'required': ['definition', 'raw_value_types', 'unit_policy', 'attachment', 'normalization'],
                'properties': {'definition': nonempty, 'raw_value_types': {'type': 'array', 'minItems': 1,
                        'items': {'enum': ['string', 'number', 'array', 'boolean', 'null', 'object']}}}}}}}
    write('ontology.schema.json', meta)
    from jsonschema import Draft202012Validator
    Draft202012Validator.check_schema(schema)
    Draft202012Validator.check_schema(meta)
    errors = list(Draft202012Validator(meta).iter_errors(ontology))
    if errors:
        raise ValueError([e.message for e in errors])
    print('Built and checked annotation and ontology JSON Schemas (DEV-only).')


if __name__ == '__main__':
    main()
