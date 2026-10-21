"""Structural checks only; passing is not semantic/human validation."""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from uuid import UUID
from jsonschema import Draft202012Validator, FormatChecker

BASE = Path(__file__).resolve().parent
KINDS = set('MATERIAL DEVICE PROPERTY PERFORMANCE ANALYTE PROCESS MECHANISM OPERATING_CONDITION MORPHOLOGY TECHNOLOGY APPLICATION OTHER'.split())
POLARITIES = {'POSITIVE', 'NEGATIVE', 'UNKNOWN'}
MODALITIES = {'ASSERTED', 'PROPOSED', 'COMPARED', 'HYPOTHETICAL', 'UNKNOWN'}
SUPPORT = {'SUPPORTED', 'CONTRADICTED', 'INSUFFICIENT', 'UNRESOLVED'}
IDENTITY = {'SAME', 'RELATED', 'BROADER', 'NARROWER', 'DIFFERENT', 'UNCERTAIN'}
SCHEMA = Draft202012Validator(json.loads((BASE/'annotation.schema.json').read_text(encoding='utf-8')), format_checker=FormatChecker())


def read_jsonl(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]


def validate_legacy(d, source, template, vocabulary,*,enforce_legacy_approval=True):
    errors = ['JSON Schema: '+'.'.join(map(str,e.absolute_path))+': '+e.message for e in SCHEMA.iter_errors(d)]

    def check(ok, msg):
        if not ok:
            errors.append(msg)

    def uuid(value, msg):
        try:
            check(str(UUID(value)) == value, msg)
        except (ValueError, TypeError, AttributeError):
            errors.append(msg)

    for field, value in template.items():
        check(field in d, 'Missing template field: ' + field)
        if field in d and value is not None:
            check(type(d[field]) is type(value), 'Template type: ' + field)
    for field in ('schema_version', 'document_id', 'revision_id', 'document_code', 'split'):
        check(d.get(field) == template[field], 'Template identity: ' + field)
    for field in ('document_id', 'revision_id', 'document_code', 'split', 'openalex_id'):
        check(d.get(field) == source[field], 'Source identity: ' + field)
    for field in ('document_id', 'revision_id'):
        uuid(d.get(field), 'Invalid UUID: ' + field)
    check(d.get('rubric_version') == vocabulary['version'], 'Rubric version mismatch')
    chunks = {c['chunk_id']: c for c in source['chunks']}
    check(len(chunks) == len(source['chunks']), 'Duplicate source chunk IDs')
    for c in chunks.values():
        uuid(c['chunk_id'], 'Invalid chunk UUID')
        digest = hashlib.sha256(c['text'].encode('utf-8')).hexdigest()
        check(digest == c['text_sha256'] == c['stored_chunk_hash'], 'Source hash mismatch')
    refs = d.get('source_chunks', [])
    check({c['chunk_id'] for c in refs} == set(chunks), 'Source scope chunk mismatch')
    for c in refs:
        check(c['chunk_id'] in chunks and all(chunks[c['chunk_id']][k] == v for k, v in c.items()), 'Source chunk reference mismatch')

    def span(s):
        uuid(s.get('span_id'), 'Invalid span UUID')
        c = chunks.get(s.get('chunk_id'))
        check(c is not None, 'Span has unknown chunk')
        if c is None:
            return
        start, end = s.get('start'), s.get('end')
        valid = type(start) is int and type(end) is int and 0 <= start < end <= len(c['text'])
        check(valid, 'Invalid span offsets')
        if valid:
            check(c['text'][start:end] == s.get('text'), 'Evidence text mismatch')
        check(s.get('document_id') == source['document_id'] and s.get('revision_id') == source['revision_id'], 'Span source provenance mismatch')
        check(s.get('source_text_sha256') == c['text_sha256'], 'Span hash mismatch')

    spans = {s['span_id']: s for s in d.get('evidence_spans', [])}
    check(len(spans) == len(d.get('evidence_spans', [])), 'Duplicate evidence IDs')
    for s in spans.values():
        span(s)
    mentions = {m['mention_id']: m for m in d['mentions']}
    check(len(mentions) == len(d['mentions']), 'Duplicate mention IDs')
    concepts = {c['concept_id']: c for c in d.get('canonical_concepts', [])}
    check(len(concepts) == len(d.get('canonical_concepts', [])), 'Duplicate concept IDs')
    for c in concepts.values():
        uuid(c['concept_id'], 'Invalid concept UUID')
        check(c['kind'] in KINDS, 'Invalid concept kind')
        check(c['instance_scope'] == source['revision_id'], 'Concept scope mismatch')
    seen_mentions = set()
    for m in mentions.values():
        uuid(m['mention_id'], 'Invalid mention UUID')
        check(set(('chunk_id', 'surface_text', 'start', 'end', 'kind', 'contextual_role', 'canonical_concept', 'coreference_group', 'evidence_span_ids', 'annotation_status')) <= set(m), 'Missing mention field')
        c = chunks.get(m['chunk_id'])
        check(c is not None, 'Mention unknown chunk')
        valid = c is not None and type(m['start']) is int and type(m['end']) is int and 0 <= m['start'] < m['end'] <= len(c['text'])
        check(valid, 'Invalid mention offsets')
        if valid:
            check(c['text'][m['start']:m['end']] == m['surface_text'], 'Mention surface mismatch')
        key = (m['chunk_id'], m['start'], m['end'], m['kind'])
        check(key not in seen_mentions, 'Duplicate exact typed mention')
        seen_mentions.add(key)
        check(m['kind'] in KINDS, 'Invalid entity kind')
        check(bool(m['contextual_role']), 'Missing contextual role')
        check(m['canonical_concept'] in concepts, 'Unknown canonical concept')
        if m['canonical_concept'] in concepts:
            check(concepts[m['canonical_concept']]['kind'] == m['kind'], 'Concept/mention kind mismatch')
        check(bool(m['evidence_span_ids']) and all(e in spans for e in m['evidence_span_ids']), 'Missing mention evidence')
        check(any(e in spans and (spans[e]['chunk_id'], spans[e]['start'], spans[e]['end'], spans[e]['text']) == (m['chunk_id'], m['start'], m['end'], m['surface_text']) for e in m['evidence_span_ids']), 'No exact mention evidence')
        if m['coreference_group']:
            uuid(m['coreference_group'], 'Invalid coreference UUID')

    def evidence(items):
        check(bool(items), 'Missing relation/identity evidence')
        for s in items:
            span(s)
            check(s.get('span_id') in spans and spans[s['span_id']] == s, 'Unregistered/mismatched evidence')

    assertion_ids = set()
    for a in d['assertions']:
        uuid(a['assertion_id'], 'Invalid assertion UUID')
        check(a['assertion_id'] not in assertion_ids, 'Duplicate assertion UUID')
        assertion_ids.add(a['assertion_id'])
        h, t = mentions.get(a['head_mention_id']), mentions.get(a['tail_mention_id'])
        check(h is not None and t is not None, 'Unknown assertion endpoint')
        rule = vocabulary['relations'].get(a['relation_type'])
        check(rule is not None, 'Unknown relation type')
        if rule and h and t:
            check(h['kind'] in rule['head_kinds'] and t['kind'] in rule['tail_kinds'], 'Relation endpoint direction/types invalid')
        check(a['polarity'] in POLARITIES, 'Invalid polarity')
        check(a['modality'] in MODALITIES, 'Invalid modality')
        check(a['support_status'] in SUPPORT, 'Invalid support status')
        evidence(a['evidence'])
        for endpoint in (h, t):
            if endpoint:
                check(any(s['chunk_id'] == endpoint['chunk_id'] and s['start'] <= endpoint['start'] and s['end'] >= endpoint['end'] for s in a['evidence']), 'Endpoint outside relation evidence')
        for q in a['qualifiers']:
            check(q['applies_to_assertion_id'] == a['assertion_id'], 'Qualifier attachment mismatch')
            qs = [spans[e] for e in q['evidence_refs'] if e in spans]
            check(bool(qs) and len(qs) == len(q['evidence_refs']), 'Missing qualifier evidence')
            check(any(s['text'] == q['raw_text'] for s in qs), 'Qualifier raw text mismatch')
            numbers = [float(n.replace('−','-')) for n in re.findall(r'[−-]?\d+(?:\.\d+)?', q['raw_text'])]
            if type(q['raw_value']) in (int, float):
                check(float(q['raw_value']) in numbers, 'Qualifier numeric value absent from raw text')
            if isinstance(q['raw_value'], list):
                check([float(v) for v in q['raw_value']] == numbers, 'Qualifier range/order mismatch')
            if q['unit']:
                check(q['unit'] in q['raw_text'], 'Qualifier unit absent from raw text')
            for s in qs:
                check(any(e['chunk_id'] == s['chunk_id'] and e['start'] <= s['start'] and e['end'] >= s['end'] for e in a['evidence']), 'Qualifier outside assertion evidence')
    decision_ids = set()
    for i in d['identity_decisions']:
        uuid(i['decision_id'], 'Invalid identity UUID')
        check(i['decision_id'] not in decision_ids, 'Duplicate identity UUID')
        decision_ids.add(i['decision_id'])
        check(i['label'] in IDENTITY, 'Invalid identity label')
        l, r = mentions.get(i['left_mention_id']), mentions.get(i['right_mention_id'])
        check(l is not None and r is not None, 'Unknown identity endpoint')
        if l and r and i['label'] in ('SAME', 'DIFFERENT'):
            check((l['canonical_concept'] == r['canonical_concept']) == (i['label'] == 'SAME'), 'Identity/canonical merge contradiction')
        evidence(i['evidence'])
    # Full source non-whitespace coverage by individually reviewed sentence spans.
    for c in chunks.values():
        covered = set()
        for review in d.get('sentence_review', []):
            s = spans.get(review['span_id'])
            check(s is not None, 'Unknown reviewed sentence')
            if s and s['chunk_id'] == c['chunk_id']:
                covered.update(range(s['start'], s['end']))
        check(all(i in covered or ch.isspace() for i, ch in enumerate(c['text'])), 'Unreviewed source characters')
    for item in d.get('unresolved', []):
        check(item['status'] == 'UNRESOLVED', 'Pending question silently resolved')
        if 'evidence' in item:
            evidence(item['evidence'])
        for field in ('head_mention_id', 'tail_mention_id'):
            if field in item:
                check(item[field] in mentions, 'Unknown unresolved-candidate endpoint')
        if item.get('category') == 'ONTOLOGY_ENDPOINT_OR_PREDICATE_GAP':
            check(d['exhaustive_relations'] is False, 'Pending relation gap claims exhaustive relations')
            check(not any(a['head_mention_id'] == item['head_mention_id'] and
                          a['tail_mention_id'] == item['tail_mention_id'] and
                          a['relation_type'] == item['proposed_relation_type'] and
                          a['support_status'] == 'SUPPORTED' for a in d['assertions']),
                  'Pending predicate candidate silently accepted')
        for aid in item.get('assertion_ids', []):
            candidates = [a for a in d['assertions'] if a['assertion_id'] == aid]
            check(bool(candidates) and all(a['support_status'] == 'UNRESOLVED' for a in candidates), 'Unresolved assertion promoted to supported')
    if enforce_legacy_approval and not vocabulary['human_approved']:
        check(any(q['question_id'] == 'Q1' and q['status'] == 'UNRESOLVED' for q in d['unresolved']), 'Missing pending schema decision')
    if d['annotation_status'].startswith('AI_DRAFT'):
        check(d['review']['primary_annotator'] is None and d['review']['secondary_annotator'] is None, 'Fabricated human annotator')
        check(d['review']['human_review_status'] == 'NOT_REVIEWED', 'AI draft claims human review')
    return errors


def validate(d,source,template,vocabulary):
    if d.get('ontology_id')=='pilot24-ontology-v1.0':
        from validate_ontology_v1 import validate as validate_v1
        return validate_v1(d,source,template,vocabulary)
    if d.get('rubric_version')=='pilot24-rubric-0.3-AUTO-FROZEN' and vocabulary.get('version')!=d['rubric_version']:
        archived=BASE/'ontology/baselines/pilot24-auto-freeze-0.3/relation_vocabulary_0.3.json'
        vocabulary=json.loads(archived.read_text(encoding='utf-8'))
    return validate_legacy(d,source,template,vocabulary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='*', type=Path)
    parser.add_argument('--ontology',choices=['v1.0','legacy-0.3'],default='v1.0')
    args = parser.parse_args()
    if args.ontology=='v1.0':
        from validate_ontology_v1 import run
        raise SystemExit(run(args.paths))
    sources = {d['document_code']: d for d in read_jsonl(BASE / 'pilot24_sources.jsonl')}
    templates = {d['document_code']: d for d in read_jsonl(BASE / 'gold_annotation_template.jsonl')}
    vocab = json.loads((BASE / 'annotations/reviews/relation_vocabulary.json').read_text(encoding='utf-8'))
    reports = []
    from campaign_paths import draft_paths
    paths = args.paths or draft_paths()
    if not paths:
        raise SystemExit('No annotation files supplied/found')
    for path in paths:
        for d in read_jsonl(path):
            errors = validate(d, sources[d['document_code']], templates[d['document_code']], vocab)
            report=dict(document_code=d['document_code'],split=d['split'], status='FAIL' if errors else 'PASS',
                errors=errors, chunks=len(d['source_chunks']), sentences=len(d['sentence_review']),
                mentions=len(d['mentions']), assertions=len(d['assertions']),
                canonical_concepts=len(d['canonical_concepts']), identity_decisions=len(d['identity_decisions']),
                unresolved_questions=len(d['unresolved']),
                unresolved_assertions=sum(a['support_status'] == 'UNRESOLVED' for a in d['assertions']),
                unresolved_relation_candidates=sum(q.get('category') == 'ONTOLOGY_ENDPOINT_OR_PREDICATE_GAP' for q in d['unresolved']),
                exhaustive_entities=d['exhaustive_entities'], exhaustive_relations=d['exhaustive_relations'],
                polarity_counts=dict(Counter(a['polarity'] for a in d['assertions'])),
                modality_counts=dict(Counter(a['modality'] for a in d['assertions'])),
                annotation_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                human_review='NOT_REVIEWED', semantic_validation='NOT_ESTABLISHED_BY_THIS_SCRIPT')
            if d['split']=='HOLDOUT':
                from campaign_paths import private_root
                target=private_root()/'reports'/f'{d["document_code"]}_validation.json'
                target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                report.pop('polarity_counts');report.pop('modality_counts')
            reports.append(report)
    output = BASE / 'annotations/reports/structural_validation.json'
    output.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(reports, ensure_ascii=True, indent=2))
    if any(r['errors'] for r in reports):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
