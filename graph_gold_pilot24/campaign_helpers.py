"""Ground and validate explicitly curated decisions; no extraction model calls."""
import json
from pathlib import Path

from build_dev_pair import BASE, Draft, TEMPLATES, uid
from validate_annotations import validate

_location=BASE/'annotations/private_holdout_location.json'
PRIVATE = Path(json.loads(_location.read_text(encoding='utf-8'))['path']) if _location.exists() else Path.home()/'.codex/private/graph_gold_pilot24'


class Record(Draft):
    def __init__(self, code):
        super().__init__(code)
        self.vocab = json.loads((BASE/'annotations/reviews/relation_vocabulary.json').read_text(encoding='utf-8'))
        self.data['rubric_version'] = self.vocab['version']
        if self.vocab.get('freeze_id'):self.data['schema_freeze_id']=self.vocab['freeze_id']
        self.data['review']['schema_decision_refs'] = ['Q1','Q2','Q3']
        self.data['review']['adjudication_status'] = 'SCHEMA_APPROVED_ANNOTATIONS_NOT_REVIEWED'

    def s(self, sentence, spec):
        self.ms(sentence, spec)

    def r(self, head, relation, tail, q=(), mode='ASSERTED', scope='STUDY_RESULT', note=None, polarity='POSITIVE', ss=None):
        h,t=self.mentions[head],self.mentions[tail]
        rule=self.vocab['relations'].get(relation)
        if not rule or h['kind'] not in rule['head_kinds'] or t['kind'] not in rule['tail_kinds']:
            return self.gap(head,relation,tail,
                note or f'{relation}: {h["kind"]} → {t["kind"]} не разрешено текущей схемой; source claim сохранён.', mode,ss,q,polarity)
        evidence=ss or list(dict.fromkeys([h['sentence_id'],t['sentence_id']]+[x[0] for x in q]))
        base_id=uid(f'{self.code}/assertion/{head}/{relation}/{tail}')
        suffix=json.dumps([q,mode,scope,polarity],ensure_ascii=False,sort_keys=True) if any(a['assertion_id']==base_id for a in self.data['assertions']) else ''
        self.rel(head,relation,tail,sentences=evidence,qualifiers=q,modality=mode,scope=scope,note=note,key_suffix=suffix)
        self.data['assertions'][-1]['polarity']=polarity

    def rs(self, lines, **kwargs):
        for line in lines.strip().splitlines():
            if line.strip(): self.r(*line.split(),**kwargs)

    def gap(self, head, predicate, tail, why, mode='ASSERTED', ss=None, qualifiers=(),polarity='POSITIVE'):
        h,t=self.mentions[head],self.mentions[tail]
        sentences=ss or list(dict.fromkeys([h['sentence_id'],t['sentence_id']]+[x[0] for x in qualifiers]))
        existing=next((q for q in self.data['unresolved'] if q.get('proposed_relation_type')==predicate and q['reason']==why),None)
        candidate=dict(candidate_id=uid(f'{self.code}/candidate/{head}/{predicate}/{tail}'),
                       head_mention_id=h['mention_id'],tail_mention_id=t['mention_id'],
                       modality=mode,polarity=polarity,support_status='UNRESOLVED',
                       qualifiers=[dict(sentence_id=s,raw_text=raw,qualifier_type=kind,raw_value=value,unit=unit)
                                   for s,raw,kind,value,unit in qualifiers])
        if existing:
            existing['candidates'].append(candidate)
            for s in sentences:
                if self.sentences[s] not in existing['evidence']: existing['evidence'].append(self.sentences[s])
            return
        issue=dict(question_id=f'{self.code}-Q{len(self.data["unresolved"])+4}',status='UNRESOLVED',
            category='ONTOLOGY_ENDPOINT_OR_PREDICATE_GAP',proposed_relation_type=predicate,
            head_mention_id=h['mention_id'],tail_mention_id=t['mention_id'],
            reason=why,evidence=[self.sentences[s] for s in sentences],candidates=[candidate],
            proposal_status='PROPOSED_DEV' if self.src['split']=='DEV' else 'UNCOVERED_FROZEN_SCHEMA',
            options={'A':f'Представить {predicate} после отдельного согласования схемы.',
                     'B':'Сохранить существующую схему и учитывать как непокрытое отношение.',
                     'C':'Оставить UNRESOLVED до содержательной проверки.'},
            preliminary_recommendation='A для DEV при подтверждении семантики; B для CALIBRATION/HOLDOUT без изменения схемы.')
        self.data['unresolved'].append(issue)

    def aliases(self):
        groups={}
        for key,m in self.mentions.items(): groups.setdefault(m['canonical_concept'],[]).append(key)
        already={(i['left_mention_id'],i['right_mention_id']) for i in self.data['identity_decisions']}
        for keys in groups.values():
            for key in keys[1:]:
                if (self.mentions[keys[0]]['mention_id'],self.mentions[key]['mention_id']) not in already:
                    self.identity(keys[0],key,'SAME','Curated source-local repetition/explicit alias; conditions and physical instances remain separate.')

    def finish(self, notes):
        self.aliases()
        self.data['canonical_concepts']=list(self.concepts.values())
        self.data['exhaustive_relations']=not bool(self.data['unresolved'])
        self.data['completeness_status']='AI_PASS_ALL_SENTENCES; UNRESOLVED_EXCLUDED_FROM_NEGATIVE_GOLD; HUMAN_REVIEW_PENDING'
        self.data['semantic_self_audit']=dict(status='AI_SELF_AUDIT_COMPLETED',notes=notes,
            limitations='Not independent human validation; completeness is an AI claim, not measured recall.')
        for c in self.data['canonical_concepts']:c['normalization_version']=self.vocab['version']
        errors=validate(self.data,self.src,TEMPLATES[self.code],self.vocab)
        if errors:raise ValueError((self.code,errors))
        folder=PRIVATE/'drafts' if self.src['split']=='HOLDOUT' else BASE/'annotations/drafts'
        path=folder/(self.code+'.jsonl')
        path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix('.jsonl.tmp');temp.write_text(json.dumps(self.data,ensure_ascii=False)+'\n',encoding='utf-8');temp.replace(path)
        print(self.code,'PASS',len(self.data['mentions']),'mentions',len(self.data['assertions']),'assertions',len(self.data['unresolved']),'unresolved')


def q(sentence,text,kind,value=None,unit=None):
    return (sentence,text,kind,text if value is None else value,unit)
