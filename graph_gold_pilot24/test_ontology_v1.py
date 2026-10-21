"""Negative DEV-only regression cases; not independent human semantic review."""
import copy
import json
import unittest

import validate_ontology_v1 as v1


class OntologyV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=v1.load_spec()
        cls.sources={json.loads(s)['document_code']:json.loads(s) for s in (v1.SPEC/'dev_sources.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()}
        cls.docs={p.stem:json.loads(p.read_text(encoding='utf-8')) for p in (v1.SPEC/'dev_drafts').glob('*.jsonl')}
        assert len(cls.sources)==len(cls.docs)==12

    def reject(self,d,fragment=None):
        errors=v1.validate(d,self.sources[d['document_code']],require_freeze=False)
        self.assertTrue(errors)
        if fragment:self.assertTrue(any(fragment in e for e in errors),(fragment,errors))

    def doc_with(self,predicate):
        for d in self.docs.values():
            if any(a['relation_type']==predicate for a in d['assertions']):return copy.deepcopy(d)
        self.fail('No DEV example for '+predicate)

    def test_all_dev_baselines(self):
        for code,d in self.docs.items():
            with self.subTest(code=code):self.assertEqual(v1.validate(d,self.sources[code],require_freeze=False),[])

    def test_specification_examples_are_accepted_dev_assertions(self):
        for predicate,rule in self.spec['relations'].items():
            with self.subTest(predicate=predicate):
                example=rule['positive_example'];d=self.docs[example['document_code']]
                a=next(a for a in d['assertions'] if a['assertion_id']==example['assertion_id'])
                mentions={m['mention_id']:m for m in d['mentions']}
                self.assertEqual(a['relation_type'],predicate)
                self.assertEqual(a['support_status'],'SUPPORTED')
                self.assertEqual(example['head'],mentions[a['head_mention_id']]['surface_text'])
                self.assertEqual(example['tail'],mentions[a['tail_mention_id']]['surface_text'])
                for field in ('polarity','modality','evidence','qualifiers'):
                    self.assertEqual(example[field],a[field])

    def test_complete_question_inventory(self):
        questions=json.loads((v1.SPEC/'source_snapshot/dev_questions.json').read_text(encoding='utf-8'))
        decisions=[json.loads(s) for s in (v1.SPEC/'adjudication_decisions.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
        self.assertEqual(len(questions),20)
        indexed={d['question_id']:d for d in decisions}
        self.assertEqual(set(indexed),{q['question_id'] for q in questions})
        self.assertEqual(len(indexed),len(decisions))
        for q in questions:
            dec=indexed[q['question_id']]
            self.assertEqual(dec['actor'],'AI')
            self.assertFalse(dec['human_approved'])
            self.assertEqual(dec['human_review_status'],'NOT_REVIEWED')
            self.assertIn(dec['decision'],['ACCEPT','MAP_TO_EXISTING','REJECT','INSUFFICIENT_EVIDENCE'])
            original={c['candidate_id'] for c in q['candidates']}
            self.assertEqual(original,{c['candidate_id'] for c in dec['candidates']})
            d=self.docs[q['document_code']];assertions={a['assertion_id'] for a in d['assertions']}
            self.assertTrue(set(dec['result_assertion_ids'])<=assertions)

    def test_current_dev_copies_match_frozen_namespace(self):
        for code in self.docs:
            self.assertEqual((v1.BASE/'annotations/drafts'/f'{code}.jsonl').read_bytes(),
                             (v1.SPEC/'dev_drafts'/f'{code}.jsonl').read_bytes())

    def test_unsupported_predicate(self):
        d=copy.deepcopy(self.docs['D001']);d['assertions'][0]['relation_type']='TRANSITIVE_TOPIC_LINK';self.reject(d,'Unknown relation type')

    def test_reversed_detection(self):
        d=self.doc_with('DETECTS');a=next(a for a in d['assertions'] if a['relation_type']=='DETECTS')
        a['head_mention_id'],a['tail_mention_id']=a['tail_mention_id'],a['head_mention_id'];self.reject(d,'direction/types')

    def test_missing_endpoint(self):
        d=copy.deepcopy(self.docs['D001']);d['assertions'][0]['tail_mention_id']='00000000-0000-0000-0000-000000000000';self.reject(d,'Unknown assertion endpoint')

    def test_modality_drift(self):
        d=copy.deepcopy(self.docs['D004']);a=next(a for a in d['assertions'] if a['modality']=='PROPOSED');a['modality']='ASSERTED';self.reject(d,'Modality drift')

    def test_negation_drift(self):
        d=copy.deepcopy(self.docs['D078']);a=next(a for a in d['assertions'] if a['polarity']=='NEGATIVE');a['polarity']='POSITIVE';self.reject(d,'Negation drift')

    def test_physical_change_not_quality_improvement(self):
        d=self.doc_with('CHANGES_PARAMETER');a=next(a for a in d['assertions'] if a['relation_type']=='CHANGES_PARAMETER');a['relation_type']='IMPROVES';self.reject(d,'Predicate drift')

    def test_change_direction_required(self):
        d=self.doc_with('CHANGES_PARAMETER');a=next(a for a in d['assertions'] if a['relation_type']=='CHANGES_PARAMETER');a['qualifiers']=[q for q in a['qualifiers'] if q['qualifier_type']!='direction'];self.reject(d,'Required qualifier')

    def test_controlled_direction_enum(self):
        d=self.doc_with('CHANGES_PARAMETER');a=next(a for a in d['assertions'] if a['relation_type']=='CHANGES_PARAMETER');q=next(q for q in a['qualifiers'] if q['qualifier_type']=='direction');q['raw_value']='sideways';self.reject(d)

    def test_joint_requirement_not_individual_negation(self):
        d=self.doc_with('MEETS_REQUIREMENT');a=next(a for a in d['assertions'] if a['relation_type']=='MEETS_REQUIREMENT')
        member=next(x for x in d['assertions'] if x['relation_type']=='HAS_MEMBER' and x['head_mention_id']==a['tail_mention_id'])
        a['tail_mention_id']=member['tail_mention_id'];self.reject(d,'Joint requirement')

    def test_qualifier_attachment(self):
        d=copy.deepcopy(self.docs['D001']);q=next(q for a in d['assertions'] for q in a['qualifiers']);q['applies_to_assertion_id']='00000000-0000-0000-0000-000000000000';self.reject(d,'attachment')

    def test_wrong_surface_unicode_offsets(self):
        d=copy.deepcopy(self.docs['D001']);d['mentions'][0]['start']+=1;self.reject(d,'surface')

    def test_missing_evidence(self):
        d=copy.deepcopy(self.docs['D001']);d['assertions'][0]['evidence']=[];self.reject(d,'evidence')

    def test_cannot_link_merge(self):
        d=copy.deepcopy(self.docs['D004']);i=next(i for i in d['identity_decisions'] if i['label']=='DIFFERENT')
        ms={m['mention_id']:m for m in d['mentions']};ms[i['right_mention_id']]['canonical_concept']=ms[i['left_mention_id']]['canonical_concept'];self.reject(d,'Identity/canonical')

    def test_version_identity(self):
        d=copy.deepcopy(self.docs['D001']);d['ontology_version']='0.3';self.reject(d,'version')

    def test_freeze_identity(self):
        d=copy.deepcopy(self.docs['D001']);d['schema_freeze_id']='other-freeze';self.reject(d,'Freeze identity')

    def test_ontology_hash(self):
        d=copy.deepcopy(self.docs['D001']);d['ontology_hash']='0'*64;self.reject(d,'ontology hash')

    def test_no_transitive_publication(self):
        d=copy.deepcopy(self.docs['D001']);d['assertions'][0]['support_kind']='INFERRED_TRANSITIVELY';self.reject(d,'Direct-source support')

    def test_no_fake_human_review(self):
        d=copy.deepcopy(self.docs['D001']);d['review']['human_review_status']='REVIEWED';self.reject(d)

    def test_electronic_layer_not_fabricated_device(self):
        d=copy.deepcopy(self.docs['D010'])
        m=next(m for m in d['mentions'] if m['contextual_role']=='electronic_charge_region')
        m['kind']='DEVICE';self.reject(d,'Electronic charge/interface structures')


if __name__=='__main__':unittest.main()
