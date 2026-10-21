"""Pin this annotation release; HOLDOUT label hashes/details stay in private storage."""
import json
from pathlib import Path
import subprocess

from common import BASE, dump, digest
from validation import check_approval, frozen, ENVELOPE
from campaign_paths import private_root

OUT=Path(__file__).resolve().parent


def main():
    assert not check_approval(),check_approval()
    target=OUT/'RELEASE_MANIFEST.json'
    if target.exists():raise SystemExit('Annotation release already sealed; do not overwrite its identity.')
    report=json.loads((OUT/'REPORT.json').read_text(encoding='utf-8'))
    assert len(report['documents'])==24 and report['structural_status']=='PASS'
    assert json.loads((OUT/'test_report.json').read_text(encoding='utf-8'))['status']=='PASS'
    private=private_root()/'evaluation_v1'
    assert not private.resolve().is_relative_to(BASE.parent.resolve())
    assert len(list((private/'holdout/drafts').glob('D*.jsonl')))==6
    assert len(list((BASE/'annotations/drafts').glob('D*.jsonl')))==18
    private_manifest=private/'RELEASE_MANIFEST.json'
    artifacts={p.relative_to(private).as_posix():digest(p) for p in sorted(private.rglob('*'))
        if p.is_file() and p!=private_manifest and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    private_value={'release_id':'pilot24-ai-drafts-approved-v1-20261021','split':'HOLDOUT',
        'ontology_id':'pilot24-ontology-v1.0','ontology_sha256':digest(frozen.SPEC/'ontology.json'),
        'artifact_sha256':artifacts,'human_review':'NOT_REVIEWED','human_gold_documents':0,
        'policy':'Private labels, source evidence, decisions, baseline versions and patches. Do not publish this manifest or its contents.'}
    if private_manifest.exists():assert json.loads(private_manifest.read_text(encoding='utf-8'))==private_value
    else:dump(private_manifest,private_value)
    public_files=[p for p in OUT.rglob('*') if p.is_file() and p!=target and '__pycache__' not in p.parts and p.suffix!='.pyc']
    public_files += [BASE/'ontology/CURRENT_STATUS.json',BASE/'ontology/approvals/pilot24-ontology-v1.0.json',
        BASE/'annotations/reviews/relation_vocabulary.json',BASE/'annotations/reviews/adjudication_decisions.jsonl']
    public_files += [BASE/'annotations/drafts'/f"{d['document_code']}.jsonl" for d in report['documents'] if d['split']=='CALIBRATION']
    value={'release_id':'pilot24-ai-drafts-approved-v1-20261021','date':'2026-10-21',
        'ontology_id':'pilot24-ontology-v1.0','ontology_status':'HUMAN_APPROVED_FOR_PILOT_V1',
        'ontology_sha256':digest(frozen.SPEC/'ontology.json'),'frozen_schema_sha256':digest(frozen.SPEC/'annotation.schema.json'),
        'technical_freeze_manifest_sha256':digest(frozen.SPEC/'FREEZE_MANIFEST.json'),
        'previous_commit_sha':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'approval_record_sha256':digest(BASE/'ontology/approvals/pilot24-ontology-v1.0.json'),
        'evaluation_envelope':ENVELOPE,'public_artifact_sha256':{p.relative_to(BASE).as_posix():digest(p) for p in sorted(public_files)},
        'private_artifact_manifest_sha256':digest(private_manifest),
        'holdout_policy':'Six HOLDOUT drafts, histories, decisions, scripts, evidence, patches and individual artifact hashes remain outside this repository. Public report contains document-level metrics/status only.',
        'structural_validation':'24/24 PASS','human_reviewed_documents':0,'human_gold_documents':0,'experiments_started':False}
    dump(target,value)
    print('Sealed public annotation release and private HOLDOUT manifest; frozen ontology unchanged.')


if __name__=='__main__':main()
