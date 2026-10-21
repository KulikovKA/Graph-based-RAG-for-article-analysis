"""Publish the validated DEV drafts and vocabulary locally; never touch evaluation inputs."""
import hashlib
import json
from pathlib import Path

SPEC = Path(__file__).resolve().parent
BASE = SPEC.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if (SPEC / 'FREEZE_MANIFEST.json').exists():
        raise SystemExit('Already frozen; integration must not rewrite sealed content.')
    baseline = SPEC.parent / 'baselines/pilot24-auto-freeze-0.3'
    manifest = json.loads((baseline / 'BASELINE_MANIFEST.json').read_text(encoding='utf-8'))
    for name, expected in manifest['preserved_files'].items():
        assert sha(baseline / name) == expected, name
    ontology = json.loads((SPEC / 'ontology.json').read_text(encoding='utf-8'))
    sources = [json.loads(s) for s in (SPEC / 'dev_sources.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
    assert len(sources) == 12 and all(s['split'] == 'DEV' for s in sources)
    copied = {}
    for source in sources:
        name = source['document_code'] + '.jsonl'
        draft = SPEC / 'dev_drafts' / name
        value = json.loads(draft.read_text(encoding='utf-8'))
        assert value['split'] == 'DEV' and value['ontology_hash'] == sha(SPEC / 'ontology.json')
        target = BASE / 'annotations/drafts' / name
        target.write_bytes(draft.read_bytes())
        copied[target.relative_to(BASE).as_posix()] = sha(target)
    adapter = {'version': ontology['ontology_id'], 'ontology_id': ontology['ontology_id'],
        'ontology_sha256': sha(SPEC / 'ontology.json'), 'status': ontology['status'],
        'authoritative_specification': 'ontology/v1.0/ontology.json',
        'legacy_baseline': 'ontology/baselines/pilot24-auto-freeze-0.3/relation_vocabulary_0.3.json',
        'approval': ontology['approval'], 'relations': ontology['relations']}
    vocab = BASE / 'annotations/reviews/relation_vocabulary.json'
    vocab.write_text(json.dumps(adapter, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    log = BASE / 'annotations/reviews/adjudication_decisions.jsonl'
    existing = [json.loads(s) for s in log.read_text(encoding='utf-8').splitlines() if s.strip()]
    # Match the repository's existing LF policy without changing any JSON record.
    log.write_bytes(log.read_bytes().replace(b'\r\n', b'\n'))
    records = [json.loads(s) for s in (SPEC / 'adjudication_decisions.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
    indexed = {r['decision_id']: r for r in existing}
    added = []
    for r in records:
        if r['decision_id'] in indexed:
            assert indexed[r['decision_id']] == r, 'Conflicting decision history'
        else:
            added.append(r)
    if added:
        with log.open('ab') as output:
            if log.stat().st_size and not log.read_bytes().endswith(b'\n'):
                output.write(b'\n')
            for r in added:
                output.write((json.dumps(r, ensure_ascii=False) + '\n').encode('utf-8'))
    report = {'status': 'PASS', 'scope': 'DEV-only local publication; no evaluation input is opened',
        'dev_drafts': copied, 'current_vocabulary_sha256': sha(vocab),
        'ai_decision_records_present': len(records), 'historical_decision_records_preserved': len(existing) - sum(r['decision_id'] in indexed for r in records),
        'baseline_bytes_verified': manifest['preserved_files'],
        'historical_schema_sha256': sha(BASE / 'annotation.schema.json'),
        'historical_freeze_sha256': sha(BASE / 'annotations/reports/DEV_ONTOLOGY_FREEZE.json'),
        'human_review': 'NOT_REVIEWED', 'human_gold_documents': 0}
    (SPEC / 'integration_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('Published 12 DEV drafts, v1 vocabulary adapter, and', len(records), 'AI decisions.')


if __name__ == '__main__':
    main()
