"""Seal public Gold metadata and a separate private HOLDOUT manifest."""
import json
from pathlib import Path

from release import BASE,OUT,RELEASE_ID,DECISION_ID,BASELINE_COMMIT,digest,dump,private_root,private_release,sources,gold_path,evaluation,check_predecessor


def main():
    target=OUT/'RELEASE_MANIFEST.json'
    if target.exists():raise SystemExit('Owner-reviewed release already sealed; do not rewrite its identity.')
    assert not evaluation.check_approval(),evaluation.check_approval()
    assert check_predecessor()
    report=json.loads((OUT/'REPORT.json').read_text(encoding='utf-8'))
    tests=json.loads((OUT/'test_report.json').read_text(encoding='utf-8'))
    assert report['human_reviewed_documents']==report['structural_pass']==24
    assert report['totals']['abstentions']==23 and tests['status']=='PASS'
    closed=private_release();private_manifest=closed/'RELEASE_MANIFEST.json'
    private_files=[p for p in closed.rglob('*') if p.is_file() and p!=private_manifest and '__pycache__' not in p.parts]
    private_files += [gold_path(s['document_code'],s['split']) for s in sources() if s['split']=='HOLDOUT']
    assert len([s for s in sources() if s['split']=='HOLDOUT'])==6
    assert all(not p.resolve().is_relative_to(BASE.parent.resolve()) for p in private_files)
    private_value=dict(dataset_id=RELEASE_ID,owner_decision_ref=DECISION_ID,annotation_status='HUMAN_REVIEWED',human_review_status='APPROVED',primary_annotator='project_owner',secondary_annotator=None,review_date='2026-10-21',review_method='manual_owner_review',artifact_sha256={p.relative_to(private_root()).as_posix():digest(p) for p in sorted(private_files)},privacy='Closed HOLDOUT labels, evidence and metadata patches. Do not publish this manifest.')
    dump(private_manifest,private_value)
    public=[p for p in OUT.rglob('*') if p.is_file() and p!=target and '__pycache__' not in p.parts and p.suffix!='.pyc']
    public += [p for p in (BASE/'annotations/gold').rglob('*') if p.is_file()]
    public += [BASE/'annotations/CURRENT_DATASET.json',BASE/'annotations/reports/HUMAN_REVIEW_STATUS.json',BASE/'annotations/reviews/adjudication_decisions.jsonl',BASE/'README.md',BASE/'evaluation_v1/test_evaluation.py']
    manifest=dict(dataset_id=RELEASE_ID,owner_decision_ref=DECISION_ID,annotation_status='HUMAN_REVIEWED',human_review_status='APPROVED',primary_annotator='project_owner',secondary_annotator=None,review_date='2026-10-21',review_method='manual_owner_review',confirmation_source='USER_CHAT_ATTESTATION',independent_secondary_review=False,data_standard='HUMAN_REVIEWED_GOLD_STANDARD',evaluation_status='OWNER_APPROVED_FOR_EVALUATION',human_reviewed_documents=24,public_gold_documents=18,private_holdout_gold_documents=6,abstentions_preserved=23,content_changes=0,ontology_id='pilot24-ontology-v1.0',ontology_sha256=digest(evaluation.frozen.SPEC/'ontology.json'),ontology_schema_sha256=digest(evaluation.frozen.SPEC/'annotation.schema.json'),ontology_freeze_manifest_sha256=digest(evaluation.frozen.SPEC/'FREEZE_MANIFEST.json'),prior_ai_release_commit=BASELINE_COMMIT,prior_ai_manifest_sha256=digest(BASE/'evaluation_v1/RELEASE_MANIFEST.json'),public_artifact_sha256={p.relative_to(BASE).as_posix():digest(p) for p in sorted(public)},private_manifest_sha256=digest(private_manifest),holdout_publication_policy='Only document-level review metadata and counts are public. Labels, quotes, evidence, patches and individual HOLDOUT hashes remain private.',experiments_started=False)
    dump(target,manifest)
    print('Sealed owner-reviewed Gold release: 24 reviewed, 18 public, 6 private, 23 abstentions unchanged.')


if __name__=='__main__':main()
