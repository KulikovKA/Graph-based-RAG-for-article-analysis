"""Metadata compatibility and source-grounding regressions; no human gold claims."""
import copy
import json
import unittest
from pathlib import Path

from validation import BASE, BASIS, frozen, validate, schema_overlay, check_approval
from campaign_paths import draft_path,private_root


class EvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources={d['document_code']:d for d in map(json.loads,(BASE/'pilot24_sources.jsonl').read_text(encoding='utf-8').splitlines())}
        cls.docs={code:json.loads(draft_path(code,s['split']).read_text(encoding='utf-8')) for code,s in cls.sources.items()}

    def reject(self,d,fragment):
        errors=validate(d,self.sources[d['document_code']])
        self.assertTrue(any(fragment in e for e in errors),(fragment,errors))

    def test_approval_and_frozen_bytes(self):
        self.assertEqual(check_approval(),[])

    def test_overlay_changes_metadata_only(self):
        original=json.loads((frozen.SPEC/'annotation.schema.json').read_text(encoding='utf-8'))
        overlay=schema_overlay()
        overlay['title']=original['title']
        overlay['properties']['assertions']['items']['properties']['source_context']['properties']['interpretation_basis']={'const':'AI_DEV_SOURCE_REVIEW'}
        for key in ['evaluation_envelope_version','annotation_provenance']:
            overlay['properties'].pop(key);overlay['required'].remove(key)
        self.assertEqual(overlay,original)

    def test_wrong_actual_split_is_rejected(self):
        d=copy.deepcopy(self.docs['D018']);d['split']='HOLDOUT'
        self.reject(d,'split identity')

    def test_false_dev_provenance_is_rejected(self):
        d=copy.deepcopy(self.docs['D018']);d['assertions'][0]['source_context']['interpretation_basis']='AI_DEV_SOURCE_REVIEW'
        self.reject(d,'Evaluation envelope')

    def test_wrong_provenance_source_split(self):
        d=copy.deepcopy(self.docs['D018']);d['annotation_provenance']['source_split']='HOLDOUT'
        self.reject(d,'provenance split')

    def test_unknown_qualifier_cannot_be_added_for_coverage(self):
        d=copy.deepcopy(self.docs['D018']);q=next(q for a in d['assertions'] for q in a['qualifiers'])
        q['qualifier_type']='NEW_EVALUATION_ONLY_METRIC';self.reject(d,'Evaluation envelope')

    def test_change_requires_direction(self):
        d=copy.deepcopy(self.docs['D021']);a=next(a for a in d['assertions'] if a['relation_type']=='CHANGES_PARAMETER')
        a['qualifiers']=[];self.reject(d,'Required qualifier')

    def test_negation_regression(self):
        d=copy.deepcopy(self.docs['D042']);a=next(a for a in d['assertions'] if a['polarity']=='NEGATIVE')
        a['polarity']='POSITIVE';self.reject(d,'Negation drift')

    def test_modality_regression(self):
        d=copy.deepcopy(self.docs['D029']);a=next(a for a in d['assertions'] if a['modality']=='PROPOSED')
        a['modality']='ASSERTED';self.reject(d,'Modality drift')

    def test_qualifier_attachment(self):
        d=copy.deepcopy(self.docs['D018']);q=next(q for a in d['assertions'] for q in a['qualifiers'])
        q['applies_to_assertion_id']='00000000-0000-0000-0000-000000000000';self.reject(d,'attachment')

    def test_no_fabricated_human_labels(self):
        d=copy.deepcopy(self.docs['D018']);d['review']['human_review_status']='APPROVED'
        self.reject(d,'Evaluation envelope')
        # This suite checks the historical AI release; a later owner-approved
        # Gold release must not invalidate its unsigned-review rejection test.
        historical=json.loads((BASE/'evaluation_v1/REPORT.json').read_text(encoding='utf-8'))
        self.assertEqual(historical['human_gold_documents'],0)

    def test_third_dev_abstention_and_evidence_are_preserved(self):
        self.assertEqual(sum(len(d['unresolved'])+len(d.get('audit_abstentions',[])) for d in self.docs.values() if d['split']=='DEV'),3)
        d=copy.deepcopy(self.docs['D024']);d['audit_abstentions'][0]['evidence'][0]['text']='invented'
        self.reject(d,'Audit abstention source evidence')

    def test_holdout_artifacts_outside_repository(self):
        private=private_root().resolve();repo=BASE.parent.resolve()
        self.assertFalse(private.is_relative_to(repo))
        holdout=[d for d in self.docs.values() if d['split']=='HOLDOUT']
        self.assertEqual(len(holdout),6)
        for d in holdout:
            code=d['document_code'];root=private/'evaluation_v1/holdout'
            for folder in ['baseline_0.3','drafts','patches','decisions','semantic_changes','sentence_audit']:
                self.assertTrue((root/folder/(code+'.jsonl')).is_file())
            self.assertFalse((BASE/'annotations/drafts'/(code+'.jsonl')).exists())

    def test_public_holdout_rows_contain_only_metrics(self):
        report=json.loads((BASE/'evaluation_v1/REPORT.json').read_text(encoding='utf-8'))
        allowed={'document_code','split','mentions','assertions','unique_canonical_triples','abstentions','sentences','status','ontology_id','human_review','human_gold','added_assertions','retired_assertions','corrected_existing_assertions','patch_replay'}
        for row in report['documents']:
            if row['split']=='HOLDOUT':self.assertLessEqual(set(row),allowed)


if __name__=='__main__':unittest.main()
