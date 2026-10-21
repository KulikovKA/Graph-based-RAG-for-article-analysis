"""Document-scoped duplicate audit; preserves every source mention/assertion.

Core triples ignore conditions for counting only. Qualified groups additionally
retain polarity, modality, assertion scope and qualifier values/units/attachment.
Neither grouping establishes a scorer or authorizes merging physical instances.
"""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent


def stable(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def audit(d):
    mentions = {m['mention_id']: m for m in d['mentions']}
    concepts = {c['concept_id']: c['canonical_name'] for c in d['canonical_concepts']}
    triples, qualified = defaultdict(list), defaultdict(list)
    for a in d['assertions']:
        triple = (mentions[a['head_mention_id']]['canonical_concept'], a['relation_type'],
                  mentions[a['tail_mention_id']]['canonical_concept'])
        triples[triple].append(a['assertion_id'])
        qualifiers = sorted(stable({k: q.get(k) for k in ('qualifier_type', 'raw_value', 'normalized_value',
                            'unit', 'comparator', 'status')}) for q in a['qualifiers'])
        tail = mentions[a['tail_mention_id']]
        lexical_qualification = tail['surface_text'] if tail['kind'] in ('PROPERTY', 'PERFORMANCE') else None
        key = stable([triple, a['polarity'], a['modality'], a['assertion_scope'],
                      a['support_status'], qualifiers, lexical_qualification])
        qualified[key].append(a['assertion_id'])
    def core(t, ids):
        return dict(head_concept_id=t[0], relation_type=t[1], tail_concept_id=t[2],
                    head=concepts[t[0]], tail=concepts[t[2]], assertion_ids=ids,
                    occurrences=len(ids))
    return dict(document_code=d['document_code'], revision_id=d['revision_id'],
        assertion_occurrences=len(d['assertions']), unique_canonical_triples=len(triples),
        repeated_core_triple_occurrences=sum(len(ids)-1 for ids in triples.values()),
        unique_qualified_claims=len(qualified),
        repeated_qualified_claim_occurrences=sum(len(ids)-1 for ids in qualified.values()),
        canonical_triples=[core(t, ids) for t, ids in triples.items()],
        repeated_qualified_groups=[dict(signature=json.loads(k), assertion_ids=ids)
                                   for k, ids in qualified.items() if len(ids)>1],
        policy='Source-local diagnostic counts, not scored gold. No mentions/assertions deleted. Core triples do not equate measurement instances.',
        human_review='NOT_REVIEWED')


if __name__ == '__main__':
    reports = []
    for p in sorted((BASE / 'annotations/drafts').glob('*.jsonl')):
        for line in p.read_text(encoding='utf-8').splitlines():
            d = json.loads(line)
            report = audit(d)
            report['draft_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
            reports.append(report)
    (BASE / 'annotations/reports/canonical_claim_audit.json').write_text(
        json.dumps(reports, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for r in reports:
        print(r['document_code'], 'occurrences', r['assertion_occurrences'],
              'unique triples', r['unique_canonical_triples'], 'qualified claims', r['unique_qualified_claims'])
