"""Validate all 24 documents under immutable v1.0; publish HOLDOUT counts only."""
import copy
import json
from collections import Counter
from pathlib import Path
import sys

from common import BASE, dump, digest
from validation import validate, check_approval, frozen, ENVELOPE, schema_overlay
sys.path.insert(0,str(BASE))
from campaign_paths import draft_path, private_root

OUT=Path(__file__).resolve().parent


def main():
    assert not check_approval(),check_approval()
    # Required phase ordering: all calibration results must exist before HOLDOUT.
    calibration=list((OUT/'calibration/reports').glob('D*.json'))
    assert len(calibration)==6 and all(json.loads(p.read_text(encoding='utf-8'))['status']=='PASS' for p in calibration)
    private=private_root()/'evaluation_v1/holdout'
    assert len(list((private/'reports').glob('D*.json')))==6
    schema=schema_overlay()
    dump(OUT/'evaluation_annotation.schema.json',schema)
    sources=[json.loads(line) for line in (BASE/'pilot24_sources.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    assert len(sources)==24 and Counter(s['split'] for s in sources)=={'DEV':12,'CALIBRATION':6,'HOLDOUT':6}
    rows=[];failures=[];private_details=[]
    for source in sources:
        path=draft_path(source['document_code'],source['split'])
        if source['split']=='HOLDOUT':assert not path.resolve().is_relative_to(BASE.parent.resolve())
        d=json.loads(path.read_text(encoding='utf-8'))
        errors=validate(d,source)
        ms={m['mention_id']:m for m in d['mentions']}
        triples={(ms[a['head_mention_id']]['canonical_concept'],a['relation_type'],ms[a['tail_mention_id']]['canonical_concept']) for a in d['assertions']}
        row=dict(document_code=d['document_code'],split=d['split'],mentions=len(d['mentions']),assertions=len(d['assertions']),unique_canonical_triples=len(triples),abstentions=len(d['unresolved'])+len(d.get('audit_abstentions',[])),sentences=len(d['sentence_review']),status='FAIL' if errors else 'PASS',ontology_id=d['ontology_id'],human_review='NOT_REVIEWED',human_gold=False)
        if source['split']!='DEV':
            root=OUT/'calibration' if source['split']=='CALIBRATION' else private
            saved=json.loads((root/'reports'/f"{d['document_code']}.json").read_text(encoding='utf-8'))
            assert saved['annotation_sha256']==digest(path)
            baseline=json.loads((root/'baseline_0.3'/path.name).read_text(encoding='utf-8'))
            patch=json.loads((root/'patches'/path.name).read_text(encoding='utf-8'))
            assert patch['baseline_sha256']==digest(root/'baseline_0.3'/path.name)
            replay=copy.deepcopy(baseline)
            for op in patch['patch']:
                key=op['path'][1:]
                if op['op']=='remove':del replay[key]
                else:replay[key]=copy.deepcopy(op['value'])
            assert replay==d
            assert (root/'drafts'/path.name).read_bytes()==path.read_bytes()
            row.update(added_assertions=saved['added_assertions'],retired_assertions=saved['retired_assertions'],corrected_existing_assertions=saved['corrected_existing_assertions'],patch_replay='PASS')
            decisions=[json.loads(l) for l in (root/'decisions'/path.name).read_text(encoding='utf-8').splitlines() if l.strip()]
            assert {q['question_id'] for q in baseline['unresolved']}=={q['question_id'] for q in decisions}
        rows.append(row)
        if errors:
            failures.append(dict(document_code=d['document_code'],errors=errors if d['split']!='HOLDOUT' else ['Private validation errors; see closed report']))
        if d['split']=='HOLDOUT':
            private_details.append(dict(metrics=row,errors=errors,annotation_sha256=digest(path),abstentions=d['unresolved'],adjudication=d.get('semantic_self_audit')))
    totals={}
    for split in ['DEV','CALIBRATION','HOLDOUT']:
        subset=[r for r in rows if r['split']==split]
        totals[split]={key:sum(r[key] for r in subset) for key in ['mentions','assertions','unique_canonical_triples','abstentions','sentences']}
        totals[split].update(documents=len(subset),passed=sum(r['status']=='PASS' for r in subset))
    report=dict(ontology_id='pilot24-ontology-v1.0',ontology_status='HUMAN_APPROVED_FOR_PILOT_V1',date='2026-10-21',ontology_hash=digest(frozen.SPEC/'ontology.json'),frozen_schema_hash=digest(frozen.SPEC/'annotation.schema.json'),evaluation_envelope=ENVELOPE,evaluation_envelope_sha256=digest(OUT/'evaluation_annotation.schema.json'),documents=rows,totals=totals,failures=failures,structural_status='PASS' if not failures else 'FAIL',human_reviewed_documents=0,human_gold_documents=0,canonical_triple_counting='Per-document revision-scoped (head canonical concept, relation type, tail canonical concept), ignoring repeated source mentions and qualifiers/polarity/modality. This is a coverage count, not an equivalence rule for qualified claims.',abstention_counting='Unresolved cases, not individual candidate edges. Unsupported qualifiers retain original values/evidence even when a supported base claim is accepted.',limitations=['Structural/provenance checks do not establish semantic correctness or recall.','Evaluation metadata adapter V1-TECH-001 is explicit; no ontology/domain/range/qualifier changes.','All HOLDOUT label-level evidence, decisions and patches are private; public rows contain counts and validation status only.','Earlier parent-context evaluation exposure and historical 0.3 freeze limitation remain documented.'],experiments_started=False)
    dump(OUT/'REPORT.json',report)
    dump(private/'final_validation_details.json',private_details)
    lines=['# Annotation migration to the approved pilot v1.0','',
        'Ontology status: **HUMAN_APPROVED_FOR_PILOT_V1** (user decision 2026-10-21). Annotation status: **AI_DRAFT / NOT_REVIEWED**. Human gold: **0/24**. No A/B/F/C/D experiments were started.','',
        'CALIBRATION was reannotated and validated first; HOLDOUT followed separately. Definitions, domain/range and qualifier schema retain the original byte hashes. The 0.3 baseline and all old evaluation drafts are preserved. Technical freeze history remains immutable; approval is a sidecar.','',
        '| Document | Split | Mentions | Assertions | Unique canonical triples | Abstention cases | Check |',
        '|---|---|---:|---:|---:|---:|---|']
    for r in rows:lines.append(f"| {r['document_code']} | {r['split']} | {r['mentions']} | {r['assertions']} | {r['unique_canonical_triples']} | {r['abstentions']} | {r['status']} |")
    lines += ['', '| Split | Documents | Mentions | Assertions | Unique triples | Abstentions | PASS |','|---|---:|---:|---:|---:|---:|---:|']
    for split,t in totals.items():lines.append(f"| {split} | {t['documents']} | {t['mentions']} | {t['assertions']} | {t['unique_canonical_triples']} | {t['abstentions']} | {t['passed']} |")
    lines += ['', 'Unique triples ignore repeated source mentions and qualifier/modality/polarity distinctions; full qualified source assertions are preserved. Abstentions count cases rather than candidate edges. Some concern an unsupported numeric qualifier on an otherwise supported base relation. They are never negative gold labels.','',
        'Checks cover exact Unicode spans, source/chunk hashes, registered evidence and endpoint coverage, allowed predicates, directed endpoints, group pairs, qualifier types/values/attachment, modality/polarity regressions, canonical identity, ontology/envelope versions, technical freeze hashes, approval identity and lossless diff replay. Structural PASS is not human semantic validation.','',
        'The only implementation adaptation is the explicit evaluation provenance envelope described in TECHNICAL_ISSUES.md. No new relation, endpoint or qualifier is introduced. The old frozen DEV validator and its reports remain unchanged.','',
        'Calibration snapshots, sources, decisions, patches and per-document audits are under calibration/. HOLDOUT equivalents and the label-level validation report are under the existing closed local storage, outside this repository. This report publishes only document counts/status for HOLDOUT.','',
        'The three accepted DEV abstentions are preserved. Evaluation gaps remain abstentions under the fixed schema; they may inform a future version only after this benchmark, without revising pilot-v1 labels or ontology silently. For independent content review and creation of Gold Dataset, follow HUMAN_REVIEW_PROTOCOL.md.','']
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
    print(json.dumps({'documents':len(rows),'passed':sum(r['status']=='PASS' for r in rows),'totals':totals,'failures':failures},ensure_ascii=True))
    return 0 if not failures else 1


if __name__=='__main__':raise SystemExit(main())
