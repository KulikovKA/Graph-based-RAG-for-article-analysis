"""Source-anchored, deterministic annotation migration. No extraction/model calls."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid5, NAMESPACE_URL

from validation import BASE, BASIS, ENVELOPE, check_approval, frozen, validate, digest
sys.path.insert(0, str(BASE))
from campaign_paths import private_root


def uid(*parts):
    return str(uuid5(NAMESPACE_URL, 'pilot24-evaluation-v1/'+'/'.join(map(str,parts))))


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')


def jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, ensure_ascii=False, separators=(',',':'))+'\n' for r in rows), encoding='utf-8', newline='\n')


class Review:
    def __init__(self, code, split):
        assert split in ('CALIBRATION','HOLDOUT')
        assert not check_approval(), check_approval()
        self.code, self.split = code, split
        self.root = BASE/'evaluation_v1/calibration' if split=='CALIBRATION' else private_root()/'evaluation_v1/holdout'
        if split=='HOLDOUT':
            assert not self.root.resolve().is_relative_to(BASE.parent.resolve())
        self.target = (BASE/'annotations/drafts' if split=='CALIBRATION' else private_root()/'drafts')/(code+'.jsonl')
        baseline = self.root/'baseline_0.3'/self.target.name
        baseline.parent.mkdir(parents=True, exist_ok=True)
        if not baseline.exists(): baseline.write_bytes(self.target.read_bytes())
        self.before = json.loads(baseline.read_text(encoding='utf-8'))
        assert self.before['split'] == split
        self.d = copy.deepcopy(self.before)
        self.source = next(json.loads(line) for line in (BASE/'pilot24_sources.jsonl').read_text(encoding='utf-8').splitlines() if json.loads(line)['document_code']==code)
        assert self.source['split'] == split
        dump(self.root/'sources'/f'{code}.json', self.source)
        self.spec = frozen.load_spec()
        self.decisions, self.changes, self.notes = [], [], {}
        self.aliases = {}

    def m(self, key):
        key = self.aliases.get(key, key)
        return next(m for m in self.d['mentions'] if m['local_key']==key)

    def se(self, sid):
        row = next(r for r in self.d['sentence_review'] if r['sentence_id']==sid)
        return next(e for e in self.d['evidence_spans'] if e['span_id']==row['span_id'])

    def note(self, sid, text):
        self.notes.setdefault(sid, []).append(text)

    def span(self, sid, text, occurrence=1):
        sentence = self.se(sid)
        positions=[]; pos=0
        while True:
            pos=sentence['text'].find(text,pos)
            if pos<0:break
            positions.append(pos);pos+=len(text)
        assert len(positions)>=occurrence,(self.code,sid,text,positions)
        start=sentence['start']+positions[occurrence-1];end=start+len(text)
        found=next((e for e in self.d['evidence_spans'] if e['chunk_id']==sentence['chunk_id'] and e['start']==start and e['end']==end),None)
        if found:return found
        result=dict(sentence, span_id=uid(self.code,'span',sentence['chunk_id'],start,end),start=start,end=end,text=text)
        self.d['evidence_spans'].append(result)
        return result

    def add_m(self, key, sid, text, kind, canonical=None, role=None, occurrence=1):
        span=self.span(sid,text,occurrence)
        found=next((m for m in self.d['mentions'] if m['chunk_id']==span['chunk_id'] and m['start']==span['start'] and m['end']==span['end'] and m['kind']==kind),None)
        if found:
            self.aliases[key]=found['local_key'];return found
        canonical=canonical or text.lower()
        concept=next((c for c in self.d['canonical_concepts'] if c['canonical_name']==canonical and c['kind']==kind),None)
        if concept is None:
            concept=dict(concept_id=uid(self.code,'concept',kind,canonical),canonical_name=canonical,kind=kind,instance_scope=self.d['revision_id'],normalization_version='pilot24-ontology-v1.0')
            self.d['canonical_concepts'].append(concept)
        m=dict(mention_id=uid(self.code,'mention',key),local_key=key,sentence_id=sid,chunk_id=span['chunk_id'],start=span['start'],end=span['end'],surface_text=text,kind=kind,contextual_role=role or 'technical_'+kind.lower(),canonical_concept=concept['concept_id'],coreference_group=None,evidence_span_ids=[span['span_id']],annotation_status='AI_DRAFT')
        self.d['mentions'].append(m)
        return m

    def add_a(self, head, predicate, tail, mode='ASSERTED', polarity='POSITIVE', qualifiers=(), sentences=None, reason='', assertion_id=None, scope='STUDY_RESULT'):
        h,t=self.m(head),self.m(tail)
        aid=assertion_id or uid(self.code,'assertion',head,predicate,tail,mode,polarity)
        if any(a['assertion_id']==aid for a in self.d['assertions']):
            assert assertion_id is None, 'Explicit assertion ID collision'
            aid=uid(self.code,'assertion',head,predicate,tail,mode,polarity,'variant',json.dumps(qualifiers,ensure_ascii=True,sort_keys=True))
        evidence=[self.se(s) for s in (sentences or list(dict.fromkeys([h['sentence_id'],t['sentence_id']]+[q[0] for q in qualifiers])))]
        a=dict(assertion_id=aid,head_mention_id=h['mention_id'],tail_mention_id=t['mention_id'],relation_type=predicate,modality=mode,polarity=polarity,support_status='SUPPORTED',qualifiers=[],evidence=evidence,annotation_status='AI_DRAFT',assertion_scope=scope,semantic_note=reason)
        for sid,text,kind,value,unit in qualifiers:
            self.attach(a,sid,text,kind,value,unit)
        self.d['assertions'].append(a)
        self.changes.append(dict(action='ADD_ASSERTION',assertion_id=aid,reason=reason))
        return a

    def attach(self,a,sid,text,kind,value=None,unit=None):
        span=self.span(sid,text)
        if not any(e['chunk_id']==span['chunk_id'] and e['start']<=span['start'] and e['end']>=span['end'] for e in a['evidence']):
            a['evidence'].append(self.se(sid))
        a['qualifiers'].append(dict(qualifier_type=kind,raw_text=text,raw_value=text if value is None else value,normalized_value=None,unit=unit,comparator='EXPLICIT_TEXT',applies_to_assertion_id=a['assertion_id'],evidence_refs=[span['span_id']],status='EXPLICIT'))

    def a(self,head,predicate,tail):
        return next(a for a in self.d['assertions'] if a['head_mention_id']==self.m(head)['mention_id'] and a['tail_mention_id']==self.m(tail)['mention_id'] and a['relation_type']==predicate)

    def retire(self,head,predicate,tail,reason):
        a=self.a(head,predicate,tail);self.d['assertions'].remove(a)
        self.changes.append(dict(action='RETIRE_ASSERTION',assertion_id=a['assertion_id'],reason=reason,original=a))
        return a

    def decide(self,qid,decision,reason,results=()):
        original=next(q for q in self.before['unresolved'] if q['question_id']==qid)
        self.decisions.append(dict(decision_id=uid(self.code,'decision',qid),question_id=qid,actor='AI',decision=decision,rationale=reason,original_question=copy.deepcopy(original),result_assertion_ids=[a['assertion_id'] for a in results],human_review_status='NOT_REVIEWED',human_approved=False))
        if decision!='INSUFFICIENT_EVIDENCE' and decision!='UNSUPPORTED_FROZEN_ONTOLOGY':
            self.d['unresolved']=[q for q in self.d['unresolved'] if q['question_id']!=qid]
        else:
            q=next(q for q in self.d['unresolved'] if q['question_id']==qid)
            q.update(current_decision=decision,current_reason=reason,ontology_id='pilot24-ontology-v1.0',proposal_status='ABSTAIN_UNDER_APPROVED_FROZEN_V1')

    def abstain(self, category, reason, evidence, original=None, base_assertion=None):
        qid=f'{self.code}-V1-A{1+sum(q["question_id"].startswith(self.code+"-V1-A") for q in self.d["unresolved"])}'
        q=dict(question_id=qid,status='UNRESOLVED',category=category,reason=reason,evidence=evidence,actor='AI',human_review_status='NOT_REVIEWED',ontology_id='pilot24-ontology-v1.0')
        if original is not None:q['original_candidate']=copy.deepcopy(original)
        if base_assertion is not None:q['base_assertion_id']=base_assertion
        self.d['unresolved'].append(q)
        return q

    def qualifiers(self,mapping=None, redundant=()):
        mapping=mapping or {}
        for a in self.d['assertions']:
            kept=[];unsupported=[]
            rule=self.spec['relations'][a['relation_type']]
            allowed=set(rule['optional_qualifiers'])|set(rule['required_qualifiers'])
            for q in a['qualifiers']:
                old=q['qualifier_type']
                if old in redundant:
                    self.changes.append(dict(action='REMOVE_REDUNDANT_LEXICAL_QUALIFIER',assertion_id=a['assertion_id'],original_qualifier=q,reason='The predicate/evidence already records this lexical causal or evidential construction; no quantitative value is lost.'))
                    continue
                q=copy.deepcopy(q)
                if old in mapping:q['qualifier_type']=mapping[old]
                if q['qualifier_type'] not in allowed:unsupported.append(q)
                else:kept.append(q)
            if unsupported:
                self.abstain('QUALIFIER_NOT_IN_FROZEN_V1','The source qualifier cannot be normalized by the frozen qualifier schema. The base claim remains only with its supported qualifiers; complete original values are retained here and in the baseline.',a['evidence'],original=dict(assertion=copy.deepcopy(a),unsupported_qualifiers=unsupported),base_assertion=a['assertion_id'])
            a['qualifiers']=kept

    def finish(self):
        assert not check_approval(),check_approval()
        d=self.d
        d.update(annotation_status='AI_DRAFT',rubric_version='pilot24-ontology-v1.0',ontology_id='pilot24-ontology-v1.0',ontology_version='1.0',schema_freeze_id='pilot24-ontology-v1.0',ontology_hash=digest(frozen.SPEC/'ontology.json'),evaluation_envelope_version=ENVELOPE)
        d['review'].update(primary_annotator=None,secondary_annotator=None,human_review_status='NOT_REVIEWED',ontology_human_approval=True,ontology_approval_scope='SCHEMA_ONLY',ontology_approval_ref='USER-ONTOLOGY-V1-APPROVAL-20261021',adjudication_status='AI_REANNOTATED_UNDER_HUMAN_APPROVED_SCHEMA_LABELS_NOT_REVIEWED')
        d['annotation_provenance']=dict(actor='AI',source_split=self.split,ontology_approval_ref='USER-ONTOLOGY-V1-APPROVAL-20261021',label_human_review='NOT_REVIEWED',ontology_changed=False,metadata_adapter='V1-TECH-001',source_snapshot_sha256=digest(self.root/'sources'/f'{self.code}.json'))
        for a in d['assertions']:
            a['support_kind']='DIRECT_SOURCE';a['relation_vocabulary_status']='HUMAN_APPROVED_SCHEMA_AI_LABEL'
            a['source_context']=dict(source_relation_type=a['relation_type'],source_modality=a['modality'],source_polarity=a['polarity'],interpretation_basis=BASIS,evidence_span_ids=[e['span_id'] for e in a['evidence']])
        for c in d['canonical_concepts']:c['normalization_version']='pilot24-ontology-v1.0'
        for r in d['sentence_review']:
            r.update(entity_pass='REVIEWED_BY_AI_FROZEN_V1',relation_pass='REVIEWED_BY_AI_FROZEN_V1',semantic_review='SOURCE_ONLY_AI_REANNOTATION_NOT_HUMAN_REVIEW')
            r.setdefault('notes',[]).extend(self.notes.get(r['sentence_id'],['Re-read this entire frozen sentence against the fixed v1 ontology; retained supported claims, local scope and identity.']))
        d['semantic_self_audit']=dict(status='AI_SOURCE_REANNOTATION_COMPLETED',ontology_changed=False,human_review='NOT_REVIEWED',notes=self.notes,limitations='Same AI source review, not independent semantic validation or measured recall.')
        d['exhaustive_relations']=not bool(d['unresolved'])
        d['completeness_status']='ALL_FROZEN_SENTENCES_REVIEWED_BY_AI_ABSTENTIONS_EXCLUDED_FROM_NEGATIVE_GOLD'
        errors=validate(d,self.source)
        if errors:raise ValueError((self.code,errors))
        # A lossless RFC6902 top-level replacement patch preserves all source mentions/history.
        patch=[]
        for key in sorted(set(self.before)|set(d)):
            if key not in d:patch.append(dict(op='remove',path='/'+key))
            elif key not in self.before:patch.append(dict(op='add',path='/'+key,value=d[key]))
            elif self.before[key]!=d[key]:patch.append(dict(op='replace',path='/'+key,value=d[key]))
        replay=copy.deepcopy(self.before)
        for op in patch:
            key=op['path'][1:]
            if op['op']=='remove':del replay[key]
            else:replay[key]=copy.deepcopy(op['value'])
        assert replay==d
        jsonl(self.root/'patches'/f'{self.code}.jsonl',[dict(document_code=self.code,baseline_sha256=digest(self.root/'baseline_0.3'/self.target.name),patch=patch)])
        jsonl(self.root/'decisions'/f'{self.code}.jsonl',self.decisions)
        jsonl(self.root/'semantic_changes'/f'{self.code}.jsonl',self.changes)
        jsonl(self.target,[d])
        jsonl(self.root/'drafts'/self.target.name,[d])
        jsonl(self.root/'sentence_audit'/self.target.name,[dict(document_code=self.code,sentence_id=r['sentence_id'],evidence=self.se(r['sentence_id']),review=r) for r in d['sentence_review']])
        before_ids={a['assertion_id'] for a in self.before['assertions']};after_ids={a['assertion_id'] for a in d['assertions']}
        semantic_fields=['head_mention_id','tail_mention_id','relation_type','modality','polarity','qualifiers']
        previous={a['assertion_id']:a for a in self.before['assertions']}
        corrected=sum(any(a[k]!=previous[a['assertion_id']][k] for k in semantic_fields) for a in d['assertions'] if a['assertion_id'] in previous)
        ms={m['mention_id']:m for m in d['mentions']}
        triples={(ms[a['head_mention_id']]['canonical_concept'],a['relation_type'],ms[a['tail_mention_id']]['canonical_concept']) for a in d['assertions']}
        report=dict(document_code=self.code,split=self.split,status='PASS',mentions=len(d['mentions']),assertions=len(d['assertions']),unique_canonical_triples=len(triples),abstentions=len(d['unresolved']),sentences=len(d['sentence_review']),added_assertions=len(after_ids-before_ids),retired_assertions=len(before_ids-after_ids),corrected_existing_assertions=corrected,baseline_sha256=digest(self.root/'baseline_0.3'/self.target.name),annotation_sha256=digest(self.target),lossless_patch_replay='PASS',ontology_id=d['ontology_id'],ontology_hash=d['ontology_hash'],envelope=ENVELOPE,human_review='NOT_REVIEWED',human_gold=False)
        dump(self.root/'reports'/f'{self.code}.json',report)
        print(self.code,'PASS',report['mentions'],'mentions',report['assertions'],'assertions',report['abstentions'],'abstentions')
        return report
