"""Owner attestation, metadata-only promotion, abstention and privacy regressions."""
import copy
import json
import unittest

from release import BASE,OUT,DECISION_ID,baseline,sources,gold_path,validate_gold,ai_projection,check_predecessor,private_release


class OwnerReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources={s['document_code']:s for s in sources()}
        cls.docs={code:json.loads(gold_path(code,s['split']).read_text(encoding='utf-8')) for code,s in cls.sources.items()}

    def test_all_24_reviewed_gold_documents(self):
        self.assertEqual(len(self.docs),24)
        for code,d in self.docs.items():
            with self.subTest(code=code):
                self.assertEqual(validate_gold(d,self.sources[code]),[])
                self.assertEqual(d['annotation_status'],'HUMAN_REVIEWED')
                self.assertEqual(d['review']['human_review_status'],'APPROVED')
                self.assertEqual(d['review']['primary_annotator'],'project_owner')
                self.assertIsNone(d['review']['secondary_annotator'])
                self.assertEqual(d['review']['review_date'],'2026-10-21')
                self.assertEqual(d['review']['review_method'],'manual_owner_review')

    def test_only_review_metadata_changed(self):
        for d in self.docs.values():self.assertEqual(ai_projection(d,baseline(d)),baseline(d))

    def test_all_23_abstentions_are_exactly_preserved(self):
        count=0
        for d in self.docs.values():
            old=baseline(d)
            self.assertEqual(d['unresolved'],old['unresolved'])
            self.assertEqual(d.get('audit_abstentions',[]),old.get('audit_abstentions',[]))
            count+=len(d['unresolved'])+len(d.get('audit_abstentions',[]))
        self.assertEqual(count,23)

    def test_second_annotator_cannot_be_fabricated(self):
        d=copy.deepcopy(self.docs['D001']);d['review']['secondary_annotator']='independent_reviewer'
        self.assertTrue(any('Gold metadata' in e for e in validate_gold(d,self.sources['D001'])))

    def test_wrong_review_date_is_rejected(self):
        d=copy.deepcopy(self.docs['D001']);d['review']['review_date']='2026-10-20'
        self.assertTrue(any('Gold metadata' in e for e in validate_gold(d,self.sources['D001'])))

    def test_missing_chat_decision_reference_is_rejected(self):
        d=copy.deepcopy(self.docs['D001']);d['review']['owner_decision_ref']='unsigned'
        self.assertTrue(any('Gold metadata' in e for e in validate_gold(d,self.sources['D001'])))

    def test_review_cannot_hide_semantic_changes(self):
        d=copy.deepcopy(self.docs['D004']);a=next(a for a in d['assertions'] if a['modality']=='PROPOSED');a['modality']='ASSERTED'
        self.assertTrue(any('content changed' in e for e in validate_gold(d,self.sources['D004'])))

    def test_review_cannot_resolve_an_abstention(self):
        d=copy.deepcopy(self.docs['D024']);d['audit_abstentions']=[]
        self.assertTrue(any('abstentions changed' in e for e in validate_gold(d,self.sources['D024'])))

    def test_private_gold_is_not_public(self):
        self.assertFalse(private_release().resolve().is_relative_to(BASE.parent.resolve()))
        self.assertEqual(len(list((BASE/'annotations/gold').glob('D*.jsonl'))),18)
        for code,s in self.sources.items():
            if s['split']=='HOLDOUT':
                self.assertFalse((BASE/'annotations/gold'/(code+'.jsonl')).exists())
                self.assertFalse(gold_path(code,'HOLDOUT').resolve().is_relative_to(BASE.parent.resolve()))

    def test_historical_ai_release_hashes_are_preserved_in_git(self):
        self.assertTrue(check_predecessor())

    def test_owner_statement_is_recorded_without_independence_claim(self):
        decision=json.loads((OUT/'OWNER_DECISION.json').read_text(encoding='utf-8'))
        self.assertEqual(decision['decision_id'],DECISION_ID)
        self.assertTrue(decision['human_review_confirmed_by_owner'])
        self.assertEqual(decision['confirmation_source'],'USER_CHAT_ATTESTATION')
        self.assertFalse(decision['independent_secondary_review'])


if __name__=='__main__':unittest.main()
