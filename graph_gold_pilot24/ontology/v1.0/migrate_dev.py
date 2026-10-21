"""Deterministic DEV-only reannotation and specification build.

python graph_gold_pilot24/ontology/v1.0/migrate_dev.py --input-dir .cache/ontology-v1-dev-only
After a clone use --input-dir graph_gold_pilot24/ontology/v1.0/source_snapshot.
Only the ten explicitly enumerated DEV-bundle files are read. No evaluation,
combined question, full-corpus, private, or historical curation path is accessed.
The root integration step alone creates the final freeze manifest and commit.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import uuid
from collections import Counter

from build_ontology import ONTOLOGY_ID, build_spec

OUT = Path(__file__).resolve().parent
INPUT_FILES = ['dev_sources.jsonl','dev_drafts_0.3.jsonl','dev_manifest.json','dev_questions.json',
               'relation_vocabulary_0.3.json','annotation_0.3.schema.json','ANNOTATION_GUIDE.md',
               'RUBRIC_0.2_WORKING.md','DEV_ONTOLOGY_FREEZE_0.3.json','README.md']

def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n',encoding='utf-8',newline='\n')

def jsonl(path, rows):
    path.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in rows),encoding='utf-8',newline='\n')

def uid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, '/'.join([ONTOLOGY_ID,*map(str,parts)])))

def digest(b): return hashlib.sha256(b).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args()
    inp=args.input_dir.resolve()
    data={f:(inp/f).read_bytes() for f in INPUT_FILES}
    sources=[json.loads(x) for x in data['dev_sources.jsonl'].decode('utf-8').splitlines()]
    originals=[json.loads(x) for x in data['dev_drafts_0.3.jsonl'].decode('utf-8').splitlines()]
    questions=json.loads(data['dev_questions.json'].decode('utf-8'))
    manifest=json.loads(data['dev_manifest.json'].decode('utf-8'))
    expected={x['document_code'] for x in manifest}
    assert len(expected)==12 and all(x['split']=='DEV' for x in manifest)
    assert {x['document_code'] for x in sources}==expected=={x['document_code'] for x in originals}
    assert len(questions)==20 and len({q['question_id'] for q in questions})==20
    assert sum(len(q['candidates']) for q in questions)==26
    assert all(d['split']=='DEV' for d in originals+sources)
    drafts=copy.deepcopy(originals)
    docs={d['document_code']:d for d in drafts}
    ss={s['document_code']:s for s in sources}
    changes=[]
    decisions=[]
    qmap={q['question_id']:q for q in questions}

    def m(code,key):
        return next(x for x in docs[code]['mentions'] if x['local_key']==key)

    def sentence(code, sid):
        d=docs[code]; row=next(x for x in d['sentence_review'] if x['sentence_id']==sid)
        return next(e for e in d['evidence_spans'] if e['span_id']==row['span_id'])

    def span(code, sid, text, occurrence=0):
        d=docs[code]; se=sentence(code,sid)
        pos=se['start']
        chunk=next(c for c in ss[code]['chunks'] if c['chunk_id']==se['chunk_id'])
        start=-1
        for _ in range(occurrence+1):
            start=chunk['text'].find(text,pos,se['end']); assert start>=0,(code,sid,text)
            pos=start+len(text)
        end=start+len(text)
        ex=next((e for e in d['evidence_spans'] if e['chunk_id']==se['chunk_id'] and e['start']==start and e['end']==end),None)
        if ex: return ex
        e={'span_id':uid(code,'span',se['chunk_id'],start,end),'document_id':d['document_id'],'revision_id':d['revision_id'],
           'chunk_id':se['chunk_id'],'start':start,'end':end,'text':text,'source_text_sha256':chunk['text_sha256']}
        d['evidence_spans'].append(e)
        return e

    def mention(code,key,sid,text,kind,canonical=None,role=None,occurrence=0):
        d=docs[code]
        assert not any(x['local_key']==key for x in d['mentions'])
        e=span(code,sid,text,occurrence)
        canonical=canonical or text
        cid=uid(code,'concept',kind,canonical)
        if not any(c['concept_id']==cid for c in d['canonical_concepts']):
            d['canonical_concepts'].append({'concept_id':cid,'canonical_name':canonical,'kind':kind,
                'instance_scope':d['revision_id'],'normalization_version':ONTOLOGY_ID})
        me={'mention_id':uid(code,'mention',key),'chunk_id':e['chunk_id'],'surface_text':text,'start':e['start'],'end':e['end'],
            'kind':kind,'contextual_role':role or 'technical_'+kind.lower(),'canonical_concept':cid,
            'coreference_group':None,'evidence_span_ids':[e['span_id']],'annotation_status':'AI_DRAFT','local_key':key,'sentence_id':sid}
        d['mentions'].append(me)
        changes.append({'document_code':code,'operation':'ADD_MENTION','new_mention_id':me['mention_id'],'reason':'Exact source mention added in the v1.0 DEV completeness/consistency pass.','local_key':key})
        return me

    def change_role(code,key,role):
        me=m(code,key)
        if me['contextual_role']!=role:
            changes.append({'document_code':code,'operation':'SET_CONTEXTUAL_ROLE','mention_id':me['mention_id'],
                'before':me['contextual_role'],'after':role,'reason':'Explicit enumeration/group role; membership does not distribute collective assertions.'})
            me['contextual_role']=role

    def qualifier(code,a,sid,typ,raw,value,unit=None):
        e=span(code,sid,raw)
        q={'qualifier_type':typ,'raw_text':raw,'raw_value':value,'normalized_value':None,'unit':unit,
           'comparator':'EXPLICIT_TEXT','applies_to_assertion_id':a['assertion_id'],'evidence_refs':[e['span_id']],'status':'EXPLICIT'}
        a['qualifiers'].append(q)
        changes.append({'document_code':code,'operation':'ADD_QUALIFIER','assertion_id':a['assertion_id'],
            'qualifier_type':typ,'raw_value':value,'raw_text':raw,'evidence_span_id':e['span_id'],
            'reason':'Source-grounded qualifier interpretation attached only to this assertion; exact raw-text evidence is registered and covered by assertion evidence.'})
        return q

    def add(code, key, rel, head, tail, sid, modality='ASSERTED',polarity='POSITIVE',scope='STUDY_RESULT',aid=None,reason='',qs=(),extra_sids=()):
        d=docs[code]
        h=m(code,head) if isinstance(head,str) else head
        t=m(code,tail) if isinstance(tail,str) else tail
        a={'assertion_id':aid or uid(code,'assertion',key),'head_mention_id':h['mention_id'],'tail_mention_id':t['mention_id'],
           'relation_type':rel,'polarity':polarity,'modality':modality,'qualifiers':[],
           'evidence':[sentence(code,sid)]+[sentence(code,x) for x in extra_sids],
           'support_status':'SUPPORTED','assertion_scope':scope,'annotation_status':'AI_DRAFT',
           'relation_vocabulary_status':'ONTOLOGY_V1_AI_ADJUDICATED','support_kind':'DIRECT_SOURCE'}
        assert not any(x['assertion_id']==a['assertion_id'] for x in d['assertions'])
        for typ,raw,value,*rest in qs: qualifier(code,a,sid,typ,raw,value,*rest)
        d['assertions'].append(a)
        changes.append({'document_code':code,'operation':'ADD_ASSERTION','new_assertion_id':a['assertion_id'],'reason':reason or 'Explicit source technical fact recovered by v1.0 review.','relation_type':rel})
        return a

    def find(code,prefix):
        found=[a for a in docs[code]['assertions'] if a['assertion_id'].startswith(prefix)]
        assert len(found)==1,(code,prefix)
        return found[0]

    def retire(code,a,reason,replacements=()):
        docs[code]['assertions'].remove(a)
        changes.append({'document_code':code,'operation':'RETIRE_ASSERTION','old_assertion_id':a['assertion_id'],
            'replacement_assertion_ids':[x['assertion_id'] if isinstance(x,dict) else x for x in replacements],'reason':reason})

    def correct(code,a,reason,**fields):
        before={k:copy.deepcopy(a.get(k)) for k in fields}
        a.update(fields)
        changes.append({'document_code':code,'operation':'CORRECT_ASSERTION','assertion_id':a['assertion_id'],
            'before':before,'after':{k:copy.deepcopy(a[k]) for k in fields},'reason':reason})

    def decide(qid,action,rationale,results,candidate_actions=None):
        q=qmap[qid]
        cs=[]
        for c in q['candidates']:
            cs.append({'candidate_id':c['candidate_id'],'original_head_mention_id':c['head_mention_id'],
                'original_tail_mention_id':c['tail_mention_id'],'original_modality':c['modality'],
                'original_polarity':c['polarity'],'decision':(candidate_actions or {}).get(c['candidate_id'],action),
                'result_assertion_ids':[a['assertion_id'] for a in results],
                'rationale':rationale})
        decisions.append({'decision_id':uid('decision',qid),'question_id':qid,'document_code':q['document_code'],
            'original_status':q['status'],'original_proposed_relation_type':q['proposed_relation_type'],
            'original_head_mention_id':q['head_mention_id'],'original_tail_mention_id':q['tail_mention_id'],
            'actor':'AI','decision':action,'adjudication_status':'AI_ADJUDICATED',
            'case_status':'UNRESOLVED' if action=='INSUFFICIENT_EVIDENCE' else 'RESOLVED',
            'rationale':rationale,'source_evidence':q['evidence'],'candidates':cs,
            'result_assertion_ids':[a['assertion_id'] for a in results],'human_approved':False,
            'human_review_status':'NOT_REVIEWED','ontology_id':ONTOLOGY_ID})

    # All historical explicit collections acquire an explicit contextual group role.
    for d in drafts:
        mids={a['head_mention_id'] for a in d['assertions'] if a['relation_type']=='HAS_MEMBER'}
        for me in d['mentions']:
            if me['mention_id'] in mids: change_role(d['document_code'],me['local_key'],'explicit_group')

    # D001: retain the source's collective process/property claim; no 3x4 edges.
    a=find('D001','dbc6e834')
    qualifier('D001',a,'S5','scope','knotting the fractured fibers, incorporating multiple sensors in series/parallel and weaving multisensor array networks integrated into clothes','collective')

    # D003: connect the explicit complete account to its explained capability.
    add('D003','mechanism-explains-stretch','EXPLAINS','mechanism5','stretch5','S5',
        reason='The conjunction of serpentine design and strain isolation allows 30% stretch; retain one joint explanation.',
        qs=[('contribution','design of a stretchable serpentine structure in the LIG electrode and strain isolation from the stiff island','joint'),('scope','design of a stretchable serpentine structure in the LIG electrode and strain isolation from the stiff island','collective')])

    # D004: event production, collective interface explanation, and local modality scope.
    q=qmap['D004-Q4'];a=add('D004','snox-causes-junction-formation','CAUSES','generate','formation','S7','PROPOSED',aid=q['candidates'][0]['candidate_id'],
        reason='We suggest scopes the result-in-formation clause; endpoints are generation and formation events.')
    decide('D004-Q4','ACCEPT','Admit CAUSES for explicitly proposed event production. Keep generation and formation as PROCESS; do not substitute junction objects.',[a])
    junctions=mention('D004','junction_group','S7','SnO 2 /SnO 2 homojunctions, SnO 2 /SnO x ( x < 2) heterojunctions, and SnO 2 /graphene heterojunctions','MORPHOLOGY',
        'joint SnO2 homojunction and heterojunction structures',role='explicit_group')
    for key in ['homo','hetero1','hetero2']:
        add('D004','junction-member-'+key,'HAS_MEMBER',junctions,key,'S7','PROPOSED')
    a=add('D004','junction-group-explains-sensitivity','EXPLAINS',junctions,'sens7','S7','PROPOSED',
        qs=[('contribution',junctions['surface_text'],'joint'),('scope',junctions['surface_text'],'collective')])
    decide('D004-Q5','ACCEPT','Admit EXPLAINS with MORPHOLOGY head. The plural which refers to the junction list collectively; replace three separately sufficient-looking candidates by one group explanation. We suggest remains PROPOSED.',[a])
    q=qmap['D004-Q6'];a=add('D004','defects-partially-explain-performance','EXPLAINS','defectgen','performance','S8','ASSERTED',aid=q['candidates'][0]['candidate_id'],
        qs=[('contribution','partly responsible','partial')])
    decide('D004-Q6','ACCEPT','The next independent sentence says is also partly responsible. The prior We suggest that syntactically scopes S7, not the declarative S8; classify S8 ASSERTED, with contribution=partial and no invented numerical fraction. This AI scope judgement remains subject to human review.',[a])

    # D060: preserve adsorption -> increased carrier parameter -> sensitivity chain.
    q=qmap['D060-Q4'];a=add('D060','adsorption-increases-holes','CHANGES_PARAMETER','adsorb4','holes','S4',aid=q['candidates'][0]['candidate_id'],
        qs=[('direction','increases hole concentration','increase'),('strength','significantly','significantly'),('evidence_basis','Electrical characterization and Raman spectroscopy measurements','experiment')])
    decide('D060-Q4','MAP_TO_EXISTING','The INCREASES proposal is represented by the newly canonical CHANGES_PARAMETER plus required direction=increase. This is a physical carrier increase and never IMPROVES by definition.',[a])
    q=qmap['D060-Q5'];a=add('D060','increased-holes-explain-sensitivity','EXPLAINS','holes','enhance','S4',aid=q['candidates'][0]['candidate_id'],
        qs=[('direction','increases hole concentration','increase')])
    decide('D060-Q5','ACCEPT','Admit EXPLAINS, repairing the candidate head from adsorption to hole concentration in its explicitly increased state. This preserves the stated intermediate chain and avoids a direct adsorption-to-sensitivity shortcut.',[a])

    # D078: distinguish electric current from the magnitude of its decrease.
    current3=mention('D078','current3','S3','current','PROPERTY','electric current')
    q=qmap['D078-Q4'];a=add('D078','exposure-decreases-current','CHANGES_PARAMETER','expose',current3,'S3',aid=q['candidates'][0]['candidate_id'],
        qs=[('direction','current decrease','decrease')])
    decide('D078-Q4','MAP_TO_EXISTING','Use CHANGES_PARAMETER(direction=decrease) for the specific current effect. Add an exact current parameter mention; the original current-decrease state remains available. No separate DECREASES predicate is needed.',[a])
    q=qmap['D078-Q5'];a=add('D078','current-decrease-depends-on-amine-count','DEPENDS_ON','decrease','number','S3',aid=q['candidates'][0]['candidate_id'],
        qs=[('strength','depends strongly','strongly')])
    decide('D078-Q5','ACCEPT','Admit DEPENDS_ON for the explicitly stated dependence of the current-decrease magnitude on amine-group count. No sign or functional law is inferred.',[a])
    q=qmap['D078-Q6'];a=add('D078','deta-electrostatic-mechanism','HAS_MECHANISM','deta_mat','interaction','S4',aid=q['candidates'][0]['candidate_id'],
        qs=[('analyte_scope','NO 2','NO2'),('outcome_scope','highest response, recovery, and long-term sensing stability','response, recovery, and long-term sensing stability')])
    decide('D078-Q6','ACCEPT','Extend HAS_MECHANISM to MATERIAL: the material is the grammatical bearer of sensing performance and the electrostatic explanation. Preserve target NO2 and the stated behavior scope.',[a])
    q=qmap['D078-Q7'];a=add('D078','impurities-increase-current-decrease-magnitude','CHANGES_PARAMETER','impurities','decrease6','S6',aid=q['candidates'][0]['candidate_id'],
        qs=[('direction','intensifying the current decrease','increase'),('target_parameter','current decrease','magnitude of current decrease')])
    decide('D078-Q7','MAP_TO_EXISTING','Map INCREASES to CHANGES_PARAMETER(direction=increase) on the magnitude of current decrease. The current itself decreases; do not reverse its physical sign.',[a])
    add('D078','current-decrease-explains-response','EXPLAINS','decrease6','response6','S6',qs=[('analyte_scope','NO 2 or SO 2','NO2 or SO2')])
    q=qmap['D078-Q8'];a=add('D078','absent-strong-nh3-interaction','HAS_MECHANISM','deta7','interaction7','S7',polarity='NEGATIVE',aid=q['candidates'][0]['candidate_id'],
        qs=[('analyte_scope','NH 3','NH3')])
    decide('D078-Q8','ACCEPT','The MATERIAL domain extension permits the explicitly absent strong interaction. Keep NEGATIVE polarity restricted to NH3 and DETA-doped graphene; no global absence of interaction is inferred.',[a])
    q=qmap['D078-Q9'];a=add('D078','deta-combined-electronic-effects','HAS_MECHANISM','deta7','effects','S7',aid=q['candidates'][0]['candidate_id'],
        qs=[('analyte_scope','NH 3','NH3'),('contribution','combined effects','joint')])
    decide('D078-Q9','ACCEPT','The later self-audit question identifies a real additional material-domain mechanism candidate. Admit the combined current/mobility effects, scoped to NH3. No quantitative cancellation or independently sufficient cause is claimed; the whole explanation also includes absent strong interaction.',[a])
    current7=mention('D078','current7','S7','current','PROPERTY','electric current')
    mobility7=mention('D078','mobility7','S7','mobility','PROPERTY','carrier mobility')
    add('D078','ndoping-increases-current','CHANGES_PARAMETER','ndoping',current7,'S7',qs=[('direction','current increase by n-doping','increase')])
    add('D078','impurities-decrease-mobility','CHANGES_PARAMETER','impurities7',mobility7,'S7',qs=[('direction','mobility decrease by charged impurities','decrease')])
    inc_event=mention('D078','current_increase_event','S7','current increase by n-doping','PROCESS','current increase due to n-doping')
    dec_event=mention('D078','mobility_decrease_event','S7','mobility decrease by charged impurities','PROCESS','mobility decrease due to charged impurities')
    add('D078','combined-involves-current-change','MECHANISM_INVOLVES','effects',inc_event,'S7')
    add('D078','combined-involves-mobility-change','MECHANISM_INVOLVES','effects',dec_event,'S7')
    compound=mention('D078','nonresponse_account','S7','absence of such a strong interaction between NH 3 and DETA-doped graphene and combined effects of current increase by n-doping and mobility decrease by charged impurities',
        'MECHANISM','joint absent-interaction and current/mobility account',role='explicit_group')
    absence=mention('D078','absent_interaction_account','S7','absence of such a strong interaction between NH 3 and DETA-doped graphene','MECHANISM','absence of strong NH3-DETA-graphene interaction')
    add('D078','nonresponse-account-absence-member','HAS_MEMBER',compound,absence,'S7')
    add('D078','nonresponse-account-effects-member','HAS_MEMBER',compound,'effects','S7')
    add('D078','joint-account-explains-nonresponse','EXPLAINS',compound,'no_response','S7',
        qs=[('contribution',compound['surface_text'],'joint'),('scope',compound['surface_text'],'collective'),('analyte_scope','NH 3','NH3')])
    # Preserve source mention of the negative outcome, but negate the base response predicate.
    base_response=mention('D078','base_response7','S7','response','PERFORMANCE','NH3 sensing response in DETA-doped graphene')
    a=find('D078','c4757807');correct('D078',a,'Avoid a negated relation to a negated outcome concept. The negative HAS_PERFORMANCE points to base response; the original no-response outcome remains the explanatory target.',tail_mention_id=base_response['mention_id'])
    qualifier('D078',a,'S7','analyte_scope','NH 3','NH3')
    a=find('D078','999a2edf');correct('D078',a,'DETA is an asserted dopant component; the sentence comparison concerns sensing outcomes, not component membership.',modality='ASSERTED')
    a=find('D078','3d2b7e9b');correct('D078',a,'The NO2 target is asserted; highest is the comparison of performance measures, not a comparative relation to the analyte.',modality='ASSERTED')
    a=find('D078','951873ee');correct('D078',a,'First-principles calculation supported the adsorption claim. Computational support is provenance, not an author proposal.',modality='ASSERTED')
    # Clear fabrication/event fact, keeping material distinct from the induced event.
    induced=mention('D078','channel_induction','S8','n-channel is easily induced','PROCESS','induction of n-channel')
    add('D078','dopant-causes-channel-induction','CAUSES','dopant',induced,'S8')

    # D035: retire the unlicensed 4x4 material/analyte grid; retain a group study.
    group=mention('D035','studied_surface_group','S1','pure and doped (B@, N@, and B–N@) graphene surfaces','MATERIAL','studied pure and doped graphene surface group',role='explicit_group')
    study=mention('D035','dft_execution','S1','density functional theory (DFT) calculations','PROCESS','DFT calculation execution on graphene gas systems')
    study_a=add('D035','dft-acts-on-studied-group','ACTS_ON',study,group,'S1',qs=[('analyte_scope','CO, CO 2, NO, and NO 2','CO, CO2, NO, and NO2'),('evidence_basis','density functional theory (DFT) calculations','calculation')])
    for key in ['pure','b','n','bn']: add('D035','surface-group-member-'+key,'HAS_MEMBER',group,key,'S1')
    for a in list(docs['D035']['assertions']):
        if a['relation_type']=='USED_FOR':
            retire('D035',a,'The source describes a joint computational study, not sixteen independently demonstrated or proposed material/gas uses. Retain one source-scoped study assertion and explicit group members.',[study_a])
    a=find('D035','ac8268e2');a['evidence'].append(sentence('D035','S1'))
    qualifier('D035',a,'S1','evidence_basis','density functional theory (DFT) calculations','calculation')
    a=add('D035','adsorption-changes-electronic-properties','CHANGES_PARAMETER','adsorb','electronic','S3','COMPARED',extra_sids=['S1'],
        qs=[('direction','change significantly','unspecified'),('comparison','compared to pure and B@ and N@graphene surfaces','pure, B-doped and N-doped graphene')])
    qualifier('D035',a,'S1','evidence_basis','density functional theory (DFT) calculations','calculation')

    # D092: one collective dependence, not the four candidate cross-product edges.
    properties=mention('D092','dependent_property_group','S2','structural and electronic properties','PROPERTY','structural and electronic property bundle',role='explicit_group')
    factors=mention('D092','structural_factor_group','S2','graphene structure and the molecular adsorption configuration','MORPHOLOGY','graphene structure and adsorption configuration bundle',role='explicit_group')
    for key in ['structural','electronic']:add('D092','property-bundle-member-'+key,'HAS_MEMBER',properties,key,'S2')
    for key in ['structure','configuration']:add('D092','factor-bundle-member-'+key,'HAS_MEMBER',factors,key,'S2')
    a=add('D092','joint-properties-depend-on-joint-structure','DEPENDS_ON',properties,factors,'S2',
        qs=[('scope','structural and electronic properties','collective'),('strength','strongly dependent','strongly')])
    decide('D092-Q4','ACCEPT','Admit DEPENDS_ON but preserve both coordinated lists as groups. All four candidate links map to one collective dependence; the abstract does not independently establish every pair in their Cartesian product.',[a])
    q=qmap['D092-Q5'];a=add('D092','interactions-cause-electronic-change-event','CAUSES','interaction','changes','S5',aid=q['candidates'][0]['candidate_id'],
        qs=[('target_parameter',"graphene's electronic properties",'graphene electronic properties'),('direction','dramatic changes','unspecified')])
    decide('D092-Q5','ACCEPT','Induce explicitly asserts production of a change event. Keep MECHANISM -> PROCESS with the target electronic parameter stated in a qualifier; the direction/magnitude is not given.',[a])
    # All results in this first-principles abstract remain calculated, even when ASSERTED.
    for a in docs['D092']['assertions']:
        if not any(q['qualifier_type'] in ['evidence_basis','epistemic_basis'] for q in a['qualifiers']):
            if not any(e['span_id']==sentence('D092','S1')['span_id'] for e in a['evidence']):
                a['evidence'].append(sentence('D092','S1'))
            qualifier('D092',a,'S1','evidence_basis','density functional computations','calculation')

    # D017: review coverage does not identify a specific mechanism.
    a=find('D017','f5394724')
    retire('D017',a,'We elaborate mechanisms and introduce devices is review organization; it does not identify a device-specific mechanism. Preserve both mentions, document this excluded discourse claim.')

    # D038: material carrier of synergy; retain purpose versus achievement.
    q=qmap['D038-Q4'];a=add('D038','material-synergy-mechanism','HAS_MECHANISM','hybrid','synergy','S1',aid=q['candidates'][0]['candidate_id'],extra_sids=['S5'])
    qualifier('D038',a,'S5','evidence_basis','This review','review')
    decide('D038-Q4','ACCEPT','MATERIAL domain extension is independently supported by the explicit synergetic effects of the two components in this DEV review. A material may bear a mechanism without inventing a DEVICE mention.',[a])
    a=find('D038','abd3e3c2');qualifier('D038',a,'S4','explanatory_basis','large surface area and well-organized structure','joint large-area and organized-structure contribution')
    for prefix in ['953faa82','cc13c2b3','91304995']:
        a=find('D038',prefix)
        a['evidence'].append(sentence('D038','S5'))
        qualifier('D038',a,'S5','evidence_basis','This review','review')

    # D026: grouped requirement negation and explicit explanatory attributions.
    requirements=mention('D026','joint_requirements','S3','two requirements','PROPERTY','joint low-noise and strong-signal requirements',role='requirement_bundle')
    add('D026','requirement-noise-member','HAS_MEMBER',requirements,'noise','S3',scope='BACKGROUND')
    add('D026','requirement-signal-member','HAS_MEMBER',requirements,'signal','S3',scope='BACKGROUND')
    q=qmap['D026-Q4'];a=add('D026','existing-materials-fail-joint-requirements','MEETS_REQUIREMENT','materials',requirements,'S3',polarity='NEGATIVE',scope='BACKGROUND',aid=q['candidates'][0]['candidate_id'],
        qs=[('joint_requirement','simultaneously satisfied','all'),('scope','two requirements','collective')])
    decide('D026-Q4','ACCEPT','Admit MEETS_REQUIREMENT for an explicit requirement bundle, repairing the candidate tail from only low noise to two requirements. NEGATIVE with joint_requirement=all means not both simultaneously; neither individual failure is inferred.',[a])
    a=add('D026','mxenes-meet-joint-requirements','MEETS_REQUIREMENT','mxene',requirements,'S4',extra_sids=['S3'])
    # The qualifier text is in S3, which is retained as additional exact evidence.
    qualifier('D026',a,'S3','joint_requirement','simultaneously satisfied','all')
    qualifier('D026',a,'S3','scope','two requirements','collective')
    add('D026','conductivity-explains-low-noise','EXPLAINS','conductivity','noise4','S4')
    add('D026','functional-surface-explains-signal','EXPLAINS','surface','signal4','S4')
    q=qmap['D026-Q5'];a=add('D026','low-noise-explains-snr','EXPLAINS','noise6','snr','S6',aid=q['candidates'][0]['candidate_id'],
        qs=[('comparison','other 2D materials','other 2D materials')])
    decide('D026-Q5','ACCEPT','The source led to attribution directly links low-noise PROPERTY to SNR PERFORMANCE; it is not a possession statement or process improvement.',[a])

    # D024: width attachment, dominant background factors, neutral tuning and abstention.
    q=qmap['D024-Q4'];a=add('D024','pore-has-width','HAS_PROPERTY','hydrogenpore','width','S3',aid=q['candidates'][0]['candidate_id'],extra_sids=['S1'],
        qs=[('width','2.5 A',2.5,'A')])
    qualifier('D024',a,'S1','evidence_basis','first principles density functional theory calculations','calculation')
    decide('D024-Q4','ACCEPT','Extend HAS_PROPERTY to MORPHOLOGY for the width of the explicit all-hydrogen-passivated pore. Preserve the literal unit A; no silent angstrom conversion.',[a])
    a=add('D024','width-explains-barrier','EXPLAINS','width','barrier','S3',extra_sids=['S1'],qs=[('pore_configuration','all-hydrogen passivated pore','all-hydrogen passivated pore')])
    qualifier('D024',a,'S1','evidence_basis','first principles density functional theory calculations','calculation')
    factors=mention('D024','transport_factor_group','S4','bulk solubility and diffusivity','PROPERTY','joint bulk-solubility and diffusivity transport factors',role='explicit_group')
    add('D024','transport-solubility-member','HAS_MEMBER',factors,'solubility','S4',scope='BACKGROUND')
    add('D024','transport-diffusivity-member','HAS_MEMBER',factors,'diffusivity','S4',scope='BACKGROUND')
    a=add('D024','dominant-membrane-transport-explanation','EXPLAINS',factors,'transport','S4',scope='BACKGROUND',
        qs=[('contribution','dominate','dominant'),('scope','bulk solubility and diffusivity','collective'),('material_configuration','traditional polymer and silica membranes','traditional polymer and silica membranes')])
    decide('D024-Q5','MAP_TO_EXISTING','Do not add DOMINATES. EXPLAINS with contribution=dominant retains its distinct strength and collective bulk-solubility/diffusivity scope in traditional membranes. Two independent sufficient causes are not asserted.',[a])
    old=find('D024','d3b20936')
    aa=add('D024','pore-engineering-tunes-selectivity','CHANGES_PARAMETER','create','selectivity5','S5','HYPOTHETICAL',
        qs=[('direction','tune selectivity','unspecified')])
    bb=add('D024','pore-engineering-tunes-diffusivity','CHANGES_PARAMETER','create','diffusivity5','S5','HYPOTHETICAL',
        qs=[('direction','tune selectivity and molecular diffusivity','unspecified')])
    retire('D024',old,'Neutral tuning of selectivity and diffusivity does not claim an optimum of graphene. Replace the broad OPTIMIZES edge with the two expressly coordinated parameter targets.',[aa,bb])
    for qid in ['D024-Q6','D024-Q7']:
        decide(qid,'INSUFFICIENT_EVIDENCE','Could have widespread impact names possible application areas but does not establish a material-to-device use or fabricated component. Keep the candidate UNRESOLVED; do not widen USED_FOR to DEVICE tails from this evidence.',[])
    a=find('D024','751f0ef9');retire('D024',a,'Backward review finds the same weak could-have-impact wording insufficient for membrane USED_FOR carbon sequestration; record a completeness abstention rather than retain an inconsistent stronger claim.')
    docs['D024'].setdefault('audit_abstentions',[]).append({'case_id':'V1-D024-A1','status':'UNRESOLVED','actor':'AI','category':'VAGUE_APPLICATION_IMPACT',
        'reason':'The source suggests possible impact on carbon sequestration, but does not establish a specific membrane use. This is an additional audit abstention, not a new historical question.',
        'evidence':[sentence('D024','S7')],'human_review_status':'NOT_REVIEWED'})

    # Register original decisions exactly once, including later Q9; never erase history.
    assert set(qmap)=={x['question_id'] for x in decisions}
    decisions.sort(key=lambda x:(x['document_code'],int(x['question_id'].split('-Q')[1])))
    decision_by_q={x['question_id']:x for x in decisions}
    for d in drafts:
        code=d['document_code']
        preserved=[]
        for q in questions:
            if q['document_code']==code and decision_by_q[q['question_id']]['case_status']=='UNRESOLVED':
                qq=copy.deepcopy(q);qq['adjudication_decision_id']=decision_by_q[q['question_id']]['decision_id']
                qq['adjudication_outcome']='INSUFFICIENT_EVIDENCE';qq['actor']='AI'
                preserved.append(qq)
        d['unresolved']=preserved
        d['ontology_id']=ONTOLOGY_ID;d['ontology_version']='1.0';d['rubric_version']=ONTOLOGY_ID
        d['schema_freeze_id']=ONTOLOGY_ID
        d['annotation_status']='AI_DRAFT'
        d['review']['human_review_status']='NOT_REVIEWED'
        d['review']['adjudication_status']='AI_DEV_ONTOLOGY_V1_ADJUDICATED_LABELS_NOT_HUMAN_REVIEWED'
        d['review']['ontology_human_approval']=False
        d['adjudication_decision_ids']=[x['decision_id'] for x in decisions if x['document_code']==code]
        d['completeness_status']='ALL_SOURCE_SENTENCES_REVIEWED_BY_AI_NOT_HUMAN_VALIDATED'
        d['exhaustive_relations']=not (d['unresolved'] or d.get('audit_abstentions'))
        d['semantic_self_audit']={'status':'AI_V1_TWO_LOGICAL_PASSES_COMPLETED','passes':['completeness','consistency'],
            'design_input':'DEV-only source snapshot','human_validation':'NOT_REVIEWED',
            'limitations':'Same AI model reviewed all sentences in two logical passes; neither independence nor measured semantic recall is established.',
            'report_refs':['COVERAGE_REPORT.md','CONSISTENCY_AUDIT.md','semantic_changes.jsonl','sentence_audit.jsonl']}
        for a in d['assertions']:
            a['annotation_status']='AI_DRAFT';a['relation_vocabulary_status']='ONTOLOGY_V1_AI_ADJUDICATED'
            a['support_kind']='DIRECT_SOURCE'
            a['source_context']={'source_relation_type':a['relation_type'],'source_modality':a['modality'],'source_polarity':a['polarity'],
                'interpretation_basis':'AI_DEV_SOURCE_REVIEW','evidence_span_ids':[e['span_id'] for e in a['evidence']]}
        for c in d['canonical_concepts']:
            c['normalization_version']=ONTOLOGY_ID
        for sr in d['sentence_review']:
            sr['entity_pass']='REVIEWED_BY_AI_V1';sr['relation_pass']='REVIEWED_BY_AI_V1'
            sr['semantic_review']='DEV_ONLY_AI_V1_COMPLETENESS_AND_CONSISTENCY_NOT_HUMAN_VALIDATED'

    # INPUT_MANIFEST pins bytes before snapshot copying; deterministic and no clock field.
    input_manifest={'scope':'DEV_ONLY','ontology_id':ONTOLOGY_ID,'files':[
        {'path':f,'sha256':digest(data[f]),'bytes':len(data[f])} for f in INPUT_FILES],
        'documents':[{k:d[k] for k in ['document_code','document_id','revision_id','revision_content_hash']} for d in sources],
        'bundle_source':'Isolated .cache/ontology-v1-dev-only export prepared by parent; only the enumerated files were read.',
        'contamination_limitation':'This semantic-design context received no evaluation content. Parent history had evaluation exposure and 0.3 freeze retry happened after calibration display; complete end-to-end independence cannot be established.'}
    snapshot=OUT/'source_snapshot';snapshot.mkdir(exist_ok=True)
    for f in INPUT_FILES:
        target=snapshot/f
        if target.resolve()!=(inp/f).resolve():target.write_bytes(data[f])
    (OUT/'dev_sources.jsonl').write_bytes(data['dev_sources.jsonl'])
    (OUT/'dev_manifest.json').write_bytes(data['dev_manifest.json'])
    dump(OUT/'INPUT_MANIFEST.json',input_manifest)
    jsonl(OUT/'adjudication_decisions.jsonl',decisions)
    jsonl(OUT/'semantic_changes.jsonl',changes)
    sentence_rows=write_sentence_audit(drafts)
    spec=build_spec(drafts,decisions,input_manifest)
    dump(OUT/'ontology.json',spec)
    ontology_hash=digest((OUT/'ontology.json').read_bytes())
    for d in drafts:d['ontology_hash']=ontology_hash
    dd=OUT/'dev_drafts';dd.mkdir(exist_ok=True)
    for d in drafts:jsonl(dd/(d['document_code']+'.jsonl'),[d])
    # Lossless deterministic patch. It preserves all original source/evidence offsets.
    patches=[]
    for old,new in zip(originals,drafts):
        ops=[]
        for k in sorted(set(old)|set(new)):
            if k not in new:ops.append({'op':'remove','path':'/'+k})
            elif k not in old:ops.append({'op':'add','path':'/'+k,'value':new[k]})
            elif old[k]!=new[k]:ops.append({'op':'replace','path':'/'+k,'value':new[k]})
        replay=copy.deepcopy(old)
        for op in ops:
            key=op['path'][1:]
            if op['op']=='remove':del replay[key]
            else:replay[key]=copy.deepcopy(op['value'])
        assert replay==new
        patches.append({'document_code':new['document_code'],'format':'RFC6902 top-level operations',
            'baseline_sha256':digest(json.dumps(old,ensure_ascii=False,sort_keys=True).encode()),
            'result_sha256':digest(json.dumps(new,ensure_ascii=False,sort_keys=True).encode()),'operations':ops})
    jsonl(OUT/'dev_migration_patch.jsonl',patches)
    stats=make_stats(originals,drafts,decisions,changes)
    dump(OUT/'migration_summary.json',stats)
    jsonl(OUT/'sentence_audit.jsonl',sentence_rows)
    write_docs(spec,originals,drafts,decisions,stats,sentence_rows)
    checks=local_checks(drafts,sources,spec,originals)
    dump(OUT/'semantic_build_checks.json',checks)
    print(json.dumps({'stats':stats,'build_checks':checks},ensure_ascii=False,indent=2))

def semantic_assertion(a):
    return {k:a[k] for k in ['head_mention_id','tail_mention_id','relation_type','polarity','modality','qualifiers','support_status','evidence']}

def make_stats(old,new,decisions,changes):
    aa={a['assertion_id']:a for d in old for a in d['assertions']}
    bb={a['assertion_id']:a for d in new for a in d['assertions']}
    corrected=[i for i in aa.keys()&bb.keys() if semantic_assertion(aa[i])!=semantic_assertion(bb[i])]
    oldmm={m['mention_id']:m for d in old for m in d['mentions']}
    newmm={m['mention_id']:m for d in new for m in d['mentions']}
    triple=lambda a,mm:(mm[a['head_mention_id']]['canonical_concept'],a['relation_type'],mm[a['tail_mention_id']]['canonical_concept'])
    return {'documents':len(new),'entity_kinds':12,'relation_types':23,
        'historical_questions':20,'historical_candidates':26,'question_decisions':dict(Counter(x['decision'] for x in decisions)),
        'candidate_decisions':dict(Counter(c['decision'] for x in decisions for c in x['candidates'])),
        'remaining_unresolved_historical_questions':sum(len(d['unresolved']) for d in new),
        'additional_audit_abstentions':sum(len(d.get('audit_abstentions',[])) for d in new),
        'baseline_mentions':len(oldmm),'final_mentions':len(newmm),
        'baseline_assertions':len(aa),'final_assertions':len(bb),
        'added_assertions':len(bb.keys()-aa.keys()),'retired_assertions':len(aa.keys()-bb.keys()),
        'semantically_corrected_existing_assertions':len(corrected),'semantic_corrected_assertion_ids':sorted(corrected),
        'metadata_only_existing_assertions':len(aa.keys()&bb.keys())-len(corrected),
        'baseline_unique_canonical_triples':len({triple(a,oldmm) for a in aa.values()}),
        'final_unique_canonical_triples':len({triple(a,newmm) for a in bb.values()}),
        'final_relation_counts':dict(sorted(Counter(a['relation_type'] for a in bb.values()).items())),
        'human_gold_documents':0,'final_human_ontology_approved':False}

SENTENCE_NOTES={
 'D001':{'S4':'Retain 84 days, 43.5 ppb theoretical LOD, and deformation metrics on their own results; room temperature attaches to gas detection.','S5':'One collective process-group improvement, with explicit members; no three-by-four distribution.','S6':'May provide/widespread monitoring remains HYPOTHETICAL.'},
 'D003':{'S3':'Laser parameter optimization retained; layer position belongs to the component claim.','S4':'NO/NO2 response and LOD values remain distinct.','S5':'Added one joint explanation of 30% stretch; individual design factors are involved components of that account.','S6':'90% RH belongs to moisture resistance; demonstrated monitoring and breath classification remain actual uses.'},
 'D004':{'S3':'Decreased oxygen ratio stays a bearer-property trend associated with phase appearance; with does not establish phase-causes-ratio.','S4':'Only direct graphene->energy transport and treatment->evaporation facilitation; no transitive shortcut.','S5':'24.7 response, 1 ppm NO2 and 150 °C share the response assertion.','S7':'Proposed generation->formation CAUSES and one collective junction->sensitivity EXPLAINS.','S8':'ASSERTED partial defect contribution outside the previous suggest-that clause; no fraction.'},
 'D010':{'S3':'Each enumerated nanocomposite is explicitly said to be synthesized and used; compositional components stay within its own formula.','S4':'Awkward source best remains only unspecified overall comparison, not a fabricated numerical ranking.','S5':'Ordered 9:1:5:5 ratio remains exactly as source; material composition unchanged.','S6':'96%/200 ppm, 30-70%RH, R²=0.998 and 4.1 ppm keep separate outcome attachments. Humidity independence does not establish a quantitative zero slope.','S7':'All mechanism, layer location and conductivity-type assertions stay PROPOSED; electronic layers/junctions are MORPHOLOGY.'},
 'D060':{'S2':'NO2 is MATERIAL dopant, NH3 is ANALYTE; improvement is evaluative.','S3':'Doped and before-doping LOD values remain distinct comparison values.','S4':'Added adsorption->hole concentration increase->sensitivity explanation; repaired Q5 head to preserve the intermediate parameter.'},
 'D078':{'S3':'Exposure decreases current; magnitude of the decrease depends on amine count.','S4':'Material mechanism admitted. Highest scopes outcomes, not component/analyte membership.','S5':'Calculated support retained as provenance; supported result ASSERTED.','S6':'Impurities increase decrease magnitude, not electric current; explanatory response link retains NO2/SO2 scope.','S7':'Retain absent strong NH3 interaction and combined electronic effects. Added current increase and mobility decrease with one collective full explanation, no quantitative cancellation. Negative HAS_PERFORMANCE targets base response.','S8':'Top dopant produces n-channel induction; no fabricated vertical gate-stack components.','S9':'Could be used remains HYPOTHETICAL, with subppq and mixture scope.'},
 'D035':{'S1':'Retired the unlicensed 4x4 use grid; add one DFT process acting on explicitly enumerated surface group with gas scope.','S2':'Calculated improvement of adsorption energy/selectivity remains evaluative in source terms, not a signed energy increase inference.','S3':'Explicit significant property change added as direction unspecified, with calculation/comparison scope.','S4':'Can be sensitive/selective remains prospective; no experimental sensor manufacture inferred.'},
 'D092':{'S1':'Potential device/material uses remain hypothetical.','S2':'One group-to-group dependence replaces four unresolved candidate cross-product links.','S3':'Stronger adsorption remains a calculated comparison, not measured sensor selectivity.','S4':'Separate defective-graphene CO/NO/NO2 result and B-doped-graphene NH3 result.','S5':'Interaction induces electronic-change event; unknown direction retained.','S6':'Two-order sensitivity advantage is calculated; calculation does not itself mean proposed.','S7':'Could be improved stays HYPOTHETICAL.'},
 'D017':{'S1':'Application list explicitly governs the material class; structural and property types remain distinct.','S2':'Potential gas sensing and stated surface properties retained; no new causal law inferred.','S4':'Review discourse about mechanisms and device types does not name a device-specific mechanism; retired generic HAS_MECHANISM.','S6':'Explicit material application list can distribute the common gas-sensing use; GO/rGO and related classes remain distinct.'},
 'D038':{'S1':'Admit material synergy mechanism and preserve review-level support.','S2':'Hybridization to improve is purpose PROPOSED; composition not generalized to every named oxide combination.','S3':'Insufficient sensitivity/response rate and long recovery are limited to some cases.','S4':'Retain facilitation of adsorption/diffusion and joint explanatory features in qualifier; no independent sufficiency by each feature.','S5':'Synthesis/assembly/application review claims remain general method/use relations, without invented parameter values.'},
 'D026':{'S3':'One negative MEETS_REQUIREMENT to ALL/noise-and-signal bundle, no independent negative member edges.','S4':'MXenes possess both required traits; add positive joint satisfaction plus conductivity->noise and surface->signal explanations.','S5':'50-100 ppb is VOC LOD range at room temperature.','S6':'Low noise explains SNR; two orders and other-2D-material comparison remain on SNR result.'},
 'D024':{'S1':'Calculated permeability/selectivity retain designed-pore scope.','S2':'Nitrogen-functionalized pore result remains separate from hydrogen-passivated pore.','S3':'MORPHOLOGY pore->width admitted with literal 2.5 A; width explains gas-specific barriers.','S4':'Bulk solubility/diffusivity collectively dominate traditional membrane transport; use EXPLAINS+dominant. Suggest scopes pore superiority, not the background where-clause.','S5':'Neutral selectivity/diffusivity tuning replaces unsupported optimality; proposed techniques remain prospective.','S6':'Explicit membrane role and gas separation use remain PROPOSED.','S7':'Impact wording insufficient for fuel-cell/gas-sensor use; keep Q6/Q7 and carbon-sequestration audit abstention. No DEVICE tail expansion.'},
}

def write_sentence_audit(drafts):
    rows=[]
    for d in drafts:
        es={e['span_id']:e for e in d['evidence_spans']}
        for sr in d['sentence_review']:
            e=es[sr['span_id']]
            aa=[a for a in d['assertions'] if any(x['chunk_id']==e['chunk_id'] and x['start']<=e['start'] and x['end']>=e['end'] for x in a['evidence'])]
            note=SENTENCE_NOTES.get(d['document_code'],{}).get(sr['sentence_id'],'Re-read exact source sentence; existing entities, roles, polarity, modality and attachments retained where supported. No additional unambiguous binary technical relation found.')
            rows.append({'document_code':d['document_code'],'sentence_id':sr['sentence_id'],'evidence_span_id':e['span_id'],
                'source_text':e['text'],'passes':['AI_COMPLETENESS','AI_CONSISTENCY'],
                'accepted_assertion_ids':[a['assertion_id'] for a in aa],'finding':note,'human_review_status':'NOT_REVIEWED'})
            sr.setdefault('notes',[]).append('v1.0: '+note)
    return rows

def local_checks(drafts,sources,spec,originals):
    errors=[]; counts=Counter()
    source={c['chunk_id']:c for s in sources for c in s['chunks']}
    for d,old in zip(drafts,originals):
        es={e['span_id']:e for e in d['evidence_spans']};mm={m['mention_id']:m for m in d['mentions']}
        for e in d['evidence_spans']:
            if source[e['chunk_id']]['text'][e['start']:e['end']]!=e['text']:errors.append([d['document_code'],'bad evidence',e['span_id']])
        for me in d['mentions']:
            if source[me['chunk_id']]['text'][me['start']:me['end']]!=me['surface_text']:errors.append([d['document_code'],'bad mention',me['mention_id']])
        for a in d['assertions']:
            rr=spec['relations'][a['relation_type']];h=mm[a['head_mention_id']];t=mm[a['tail_mention_id']]
            if h['kind'] not in rr['head_kinds'] or t['kind'] not in rr['tail_kinds']:errors.append([d['document_code'],'domain/range',a['assertion_id']])
            for k,rule in rr['required_qualifiers'].items():
                if not any(q['qualifier_type']==k and q['raw_value'] in rule['enum'] for q in a['qualifiers']):errors.append([d['document_code'],'required qualifier',a['assertion_id'],k])
            for q in a['qualifiers']:
                if q['applies_to_assertion_id']!=a['assertion_id']:errors.append([d['document_code'],'attachment',a['assertion_id']])
                if q['qualifier_type'] not in spec['qualifiers']:errors.append([d['document_code'],'unknown qualifier',q['qualifier_type']])
                if not q['evidence_refs'] or not any(es[x]['text']==q['raw_text'] for x in q['evidence_refs']):errors.append([d['document_code'],'raw qualifier evidence',a['assertion_id'],q['qualifier_type']])
                for eid in q['evidence_refs']:
                    e=es[eid]
                    if not any(e['chunk_id']==ae['chunk_id'] and ae['start']<=e['start'] and e['end']<=ae['end'] for ae in a['evidence']):errors.append([d['document_code'],'qualifier outside assertion evidence',a['assertion_id'],q['qualifier_type']])
            counts['assertions']+=1
        # Existing mention/evidence offsets are immutable; added spans are allowed.
        for me in old['mentions']:
            new=mm[me['mention_id']]
            assert all(new[k]==me[k] for k in ['start','end','surface_text','chunk_id','kind','canonical_concept'])
        for e in old['evidence_spans']:assert es[e['span_id']]==e
        assert d['review']['human_review_status']=='NOT_REVIEWED'
        counts['documents']+=1;counts['sentences']+=len(d['sentence_review'])
    return {'status':'PASS' if not errors else 'FAIL','checks':'Local build: exact spans, unchanged original offsets/evidence, domains, required qualifier values, qualifier evidence/attachment and AI-only review status. Repository validator/freeze checks are separate.','counts':dict(counts),'errors':errors}

def write_docs(spec,old,new,decisions,stats,sentence_rows):
    # Markdown docs are generated from the same machine definitions and decisions.
    rel=['# Ontology v1.0 relation definitions','', 'Status: TECHNICALLY_FROZEN_PENDING_HUMAN_APPROVAL. Semantic design input: the isolated 12-document DEV bundle. All examples below are exact frozen source evidence. Positive annotation examples may contain explicit negative source claims; polarity is shown.', '', 'Each predicate is directed. The machine constraints, controlled qualifier values, endpoint pairs and examples are authoritative in `ontology.json`. Unknown author stance or polarity remains a candidate, never a supported assertion. All groups obey the shared no-distribution/no-Cartesian-product policy.', '']
    for name,r in spec['relations'].items():
        ex=r['positive_example']
        rel += ['## '+name,'',r['definition'],'',f"Direction: `{r['direction']}`. Domain: {', '.join(r['head_kinds'])}. Range: {', '.join(r['tail_kinds'])}.",'',
            'Required qualifiers: '+(json.dumps(r['required_qualifiers'],ensure_ascii=False) if r['required_qualifiers'] else 'none')+'.',
            'Optional qualifiers: '+', '.join(r['optional_qualifiers'])+'.','',
            'Polarity: '+', '.join(r['supported_polarities'])+'. Modality: '+', '.join(r['supported_modalities'])+'.','',
            f"DEV example: **{ex['document_code']}**, `{ex['assertion_id']}`: {ex['head']} → {ex['tail']} ({ex['polarity']}, {ex['modality']}).",'']
        for e in ex['evidence']:
            rel += [f"Evidence: chunk `{e['chunk_id']}`, Unicode [{e['start']},{e['end']}), SHA-256 `{e['source_text_sha256']}`.",'', '> '+e['text'],'']
        rel += ['Contrast: '+r['contrast'],'','Difference: '+r['nearest_relations'],'','Ambiguity: '+r['ambiguity_policy'],'','Groups: '+r['group_policy'],'']
    (OUT/'RELATION_DEFINITIONS.md').write_text('\n'.join(rel),encoding='utf-8',newline='\n')
    ent=['# Entity definitions and identity','', 'The 12 existing kinds are retained. Mentions have a contextual role and exact Unicode spans. A source may refer to a chemical as a dopant in one clause and as an analyte in another; the role does not change chemical identity. Groups use an existing semantic kind and an explicit group role. A mixed requirement bundle uses PROPERTY with contextual_role=requirement_bundle.', '']
    for k,v in spec['entities'].items():
        ent += ['## '+k,'',v['definition'],'','Examples: '+v['examples']+'.','', 'Boundary: '+v['boundary'],'','Canonicalization: '+v['canonicalization'],'']
    ent += ['## Context, identity and source scope','',
        'D010 electron accumulation and depletion layers and p–n junctions are MORPHOLOGY; the manufactured sensing/electrode layer in D003 is DEVICE. D004 formation is PROCESS, while the junctions it produces are MORPHOLOGY. D078 charged impurities are electronic structure, not a new material formulation by inference.', '',
        'Use SAME only for source-supported aliases or co-reference. Related class membership, chemical similarity, shared role, and a material serving as a device component never establish SAME. Keep graphene ≠ GO ≠ rGO and separate dopants, stoichiometries, pore passivations, and device configurations. A concept identifier is not proof that two measurements came from the same experimental instance. Preserve original cannot-link decisions. New mentions retain revision-local instance scope and deterministic identifiers.', '',
        'A coordinated list is not automatically an entity identity. HAS_MEMBER expresses explicit enumeration. PROPERTY→PERFORMANCE membership is allowed only for a requirement bundle; other admitted member pairs share kind. No group assertion distributes without independent source support.']
    (OUT/'ENTITY_DEFINITIONS.md').write_text('\n'.join(ent)+'\n',encoding='utf-8',newline='\n')
    rubric='''# Annotation rubric v1.0

Use only frozen source chunks. Annotation remains AI_DRAFT and NOT_REVIEWED by humans. Technical freeze of this specification is distinct from final human ontology approval and from independent human review of any label.

1. Re-read every sentence. Mark all source-expressed technical entities and claims, including background, limitations, comparisons and proposed mechanisms. Do not treat unannotated language as a negative label. Record discourse-only or genuinely unrepresentable claims as documented exclusions/abstentions.
2. Copy exact Unicode [start,end) spans relative to the chunk. Never rewrite source text, chemical spacing or units. A mention must have a kind, contextual role, source evidence and revision-scoped canonical concept. Source hashes and offsets are immutable.
3. Select the most specific supported predicate. Event production is CAUSES; enabling is FACILITATES; attribution is EXPLAINS; physical parameter change is CHANGES_PARAMETER with required direction. Better performance is IMPROVES only when the source evaluates it as better. Neutral tuning does not establish an optimum.
4. Preserve logical scope. HAS_MECHANISM points from device/material to an explanatory account; EXPLAINS points from account/factor to outcome. Keep intermediate source-expressed states, such as adsorption → hole concentration increase → sensitivity, and never infer a transitive direct causal assertion.
5. Distinguish author modality from epistemic provenance. ASSERTED includes results calculated by DFT. PROPOSED requires author suggestion/proposal. HYPOTHETICAL covers possibility/goal. COMPARED describes a comparison and preserves the named comparator. A qualifier records calculation/experiment/review support separately. UNKNOWN remains unresolved.
6. NEGATIVE requires explicit source negation. Its scope may be a target, configuration or conjunction. Not only does not negate the following positive claim. A negative response relation points to a base-response concept; a positive explanatory relation may point to the explicit nonresponse outcome. Absence in an abstract is never negative evidence.
7. Give every qualifier its literal raw_text, raw_value, unit, applies_to_assertion_id and exact evidence_refs. Keep outcome, target, concentration, temperature, duration, comparator and configuration attached to the correct assertion. Do not migrate an LOD value to response or a humidity range to an unsupported response-flatness claim. Preserve source A for D024 pore width.
8. Represent explicit collective claims with exact group mentions, contextual roles and HAS_MEMBER. Never manufacture a Cartesian product. A negative MEETS_REQUIREMENT with joint_requirement=all and scope=collective is NOT(all requirements), with no member-level negative consequences. Partial and dominant explanation strengths are qualitative contribution qualifiers; never invent numerical fractions.
9. Keep canonical chemistry and device configurations distinct. SAME requires local alias/co-reference support; RELATED/BROADER/NARROWER are not SAME. Preserve cannot-link rules. Material, device role and experimental instance remain different identity levels.
10. Decide every DEV question as ACCEPT, MAP_TO_EXISTING, REJECT or INSUFFICIENT_EVIDENCE. Preserve question/candidate identifiers, original evidence, rationale and result assertion links. Insufficient cases remain UNRESOLVED; rejected originals remain in the decision snapshot. AI decisions never imply human approval.
11. Run separate completeness and consistency reasoning passes. Structural validation checks spans, constraints and provenance; it cannot prove semantic correctness or recall. Source_context is a recorded AI interpretation for regression detection, not an independent source of truth.
12. Freeze the resulting ontology before any future evaluation annotation. Record immutable file hashes, source identity and content commit separately in FREEZE_MANIFEST.json. No evaluation-driven silent changes are allowed; later gaps must be reported under the frozen vocabulary.

Reproduce with `python graph_gold_pilot24/ontology/v1.0/migrate_dev.py --input-dir graph_gold_pilot24/ontology/v1.0/source_snapshot`. The script reads only the ten enumerated DEV files and writes its own v1.0 artifacts. `dev_migration_patch.jsonl` losslessly reconstructs the migration from the original DEV drafts; `semantic_changes.jsonl` explains semantic edits separately from ontology/source-context metadata. Repository integration supplies schema, validator, freeze hashes and commit identity.
'''
    (OUT/'ANNOTATION_RUBRIC.md').write_text(rubric,encoding='utf-8',newline='\n')
    log=['# DEV adjudication decision log','', 'Actor: AI. Final human ontology approval: false. Annotation human review: NOT_REVIEWED. This log records design adjudication, not gold approval. The immutable input snapshot retains every original question, candidate and evidence. Machine records are in `adjudication_decisions.jsonl`.', '',
        '## Historical 19 → 20 reconciliation','',
        'The 0.3 freeze reports 19 unresolved DEV questions. The isolated current DEV review bundle contains 20 unique question IDs and 26 candidate assertions. D078-Q9 is the later semantic self-audit addition about combined current-increase/mobility-decrease effects. The other 19 questions account for the earlier set; Q9 is retained and explicitly decided here. The historical 0.3 report is not edited or retroactively restated as 20. This explanation follows the supplied question provenance and old count; this isolated task does not reopen prior curation scripts or evaluation reports.', '',
        '| Question | Original proposal | Decision | Candidates | Result assertions |','|---|---|---|---:|---|']
    for x in decisions:
        log.append(f"| {x['question_id']} | {x['original_proposed_relation_type']} | {x['decision']} | {len(x['candidates'])} | {', '.join('`'+i+'`' for i in x['result_assertion_ids']) or 'UNRESOLVED'} |")
    for x in decisions:
        log += ['', '## '+x['question_id'], '',x['rationale'],'','Candidate links: '+', '.join('`'+c['candidate_id']+'`' for c in x['candidates'])+'.','']
        for e in x['source_evidence']:log += [f"Exact evidence: `{e['chunk_id']}` [{e['start']},{e['end']}).",'', '> '+e['text'],'']
    log += ['## Approval separation','', 'Earlier user Q1–Q6 instructions are design constraints, not independent annotation review. The three D004 decisions and two D060 decisions are implemented with explicit AI source interpretation. Other cases are AI adjudications authorized by the task. Technical freeze can be automatic; final human ontology approval remains false, and human gold remains 0/12 DEV.']
    (OUT/'DECISION_LOG.md').write_text('\n'.join(log)+'\n',encoding='utf-8',newline='\n')
    coverage=['# DEV completeness audit','',f"All 12 DEV documents and all {len(sentence_rows)} frozen sentences were re-read in a distinct logical completeness pass. This is an AI self-audit, not measured recall or independent review. `sentence_audit.jsonl` records every sentence, its exact source text, retained assertion links and finding.",'',
        '| Document | Sentences | Baseline assertions | v1.0 assertions | Finding |','|---|---:|---:|---:|---|']
    for o,n in zip(old,new):
        code=n['document_code'];finding=' '.join(SENTENCE_NOTES.get(code,{}).values())
        coverage.append(f"| {code} | {len(n['sentence_review'])} | {len(o['assertions'])} | {len(n['assertions'])} | {finding} |")
    coverage += ['', '## Vocabulary sufficiency and uncovered statements','',
        'Five predicates are added because existing meanings would lose distinct DEV facts: CAUSES, EXPLAINS, CHANGES_PARAMETER, DEPENDS_ON and MEETS_REQUIREMENT. INCREASES and DECREASES are one signed parameter predicate; direction is compulsory. DOMINATES is EXPLAINS with contribution=dominant. HAS_MECHANISM admits MATERIAL, HAS_PROPERTY admits MORPHOLOGY, and HAS_MEMBER admits the explicit morphology/mechanism bundles and mixed requirement members. USED_FOR is not extended to DEVICE tails.', '',
        'D024-Q6 and D024-Q7 remain INSUFFICIENT_EVIDENCE: possible impact on fuel cells/gas sensors is weaker than a use claim. The same backward rule retires carbon-sequestration use, retained as V1-D024-A1 audit abstention. These are semantic insufficiency, not a reason to invent a relation. The rubric still represents explicit proposed membrane/gas-separation use.', '',
        'D017 review organization (we discuss mechanisms and introduce devices) does not identify a device-specific mechanism. This is a documented discourse exclusion, not a missing relation type. D035 the sixteen material-by-gas uses are replaced by one group study claim: a computational investigation is not independent demonstration of every pair. D024 neutral parameter tuning is captured by CHANGES_PARAMETER with unspecified direction; no new optimum relation is needed.', '',
        'Parameter changes of known sign (D060 carrier increase, D078 current and mobility changes) use direction. D004 a bearer oxygen-ratio trend with associated phase appearance remains HAS_PROPERTY+trend because with does not name a causal factor. D010 humidity independence retains its humidity range on the performance claim; a numerical unchanged response or derivative cannot be inferred. Unspecified electronic change (D035/D092) is supported without an invented sign.', '',
        'Qualitative source evaluations, first-principles provenance, comparative baselines, local conditions, source-reported limitations and collective explanations are supported. The pilot does not encode full equations, quantitative causal effect sizes, independent sensor instances absent source identity, or vague impact as concrete deployment. These omissions are acceptable because the abstracts do not establish those facts, and no unsupported labels are manufactured.', '',
        '## Counts','', '```json',json.dumps(stats,ensure_ascii=False,indent=2),'```','',
        'All historical 20 questions receive a decision; 2 remain unresolved from genuine insufficient evidence. One additional backward-audit abstention is kept separately, so the total unresolved cases are 3. No original candidate is silently removed from the journal. Structural checks are reported separately from this semantic claim.']
    (OUT/'COVERAGE_REPORT.md').write_text('\n'.join(coverage)+'\n',encoding='utf-8',newline='\n')
    consistency='''# DEV semantic consistency audit

This was the second logical pass over all 12 DEV abstracts after completeness review. It is a self-audit by the same AI, not an independent model/human review. Structural PASS cannot prove these semantic judgements. Every historical source/evidence span and original mention span is preserved; additions have exact Unicode offsets. `semantic_changes.jsonl` records edit reasons and replacements, and `dev_migration_patch.jsonl` is replay-checked.

| Boundary | Cross-document check and result |
|---|---|
| CAUSES / FACILITATES / EXPLAINS | D004 generation produces formation under PROPOSED; graphene promotes transport and treatment facilitates evaporation, without a transitive graphene edge. Junctions collectively explain sensitivity. D092 interactions induce a change event. D078 a dopant induces channel formation. |
| INCREASES / IMPROVES | D060 increased holes uses CHANGES_PARAMETER; sensitivity improvement remains IMPROVES. D078 increase in magnitude of current decrease is not current increase. Explicit n-doping current increase and impurity mobility decrease have opposite signed parameters. |
| OPTIMIZES / IMPROVES / neutral tuning | D003 explicit layer optimization is retained. D024 tuning parameters does not establish an optimum; old OPTIMIZES is replaced by direction-unspecified parameter effects. |
| DEPENDS_ON / HAS_PROPERTY | D078 dependence on amine count is distinct from possession of current response/count. D092 joint property dependence is one group-to-group relation, not four ungrounded independent pairwise effects. |
| HAS_COMPONENT / HAS_MEMBER | D010 slash compositions identify physical constituents within each formula. Enumerated nanocomposites and gas lists are membership. D026 joint requirements are a bundle with mixed property/performance members, without two failures. |
| HAS_MECHANISM / EXPLAINS | D078 and D038 materials can bear mechanisms; this extension is supported by separate DEV sources. Explanation points to an outcome. A review mentioning mechanisms/devices without identification is excluded in D017. |
| USED_FOR / FUNCTIONS_AS / DETECTS | D024 material functions as a proposed membrane and membrane is proposed for separation. Vague possible impact on devices does not establish use. D060 NO2 dopant is not confused with NH3 analyte. D003 actual monitoring/breath uses remain distinct from target detection. |
| HAS_PROPERTY / HAS_PERFORMANCE | Carrier concentration, pore width, conductivity and noise are physical properties. Sensitivity, selectivity, response and LOD are task performance. D026 property noise can explain performance SNR; it is not retyped merely to fit an edge. |
| Electronic structure / material / device | D010 accumulation/depletion layers and junctions are MORPHOLOGY with the stated material location; proposal modality is preserved on the whole account. D003 manufactured electrode/sensing layer is DEVICE. D004 formation events remain PROCESS. |
| Modality / calculation | D035 and D092 provenance is calculated, separately from author stance. D078 calculation-supported adsorption is ASSERTED. D004 suggested junction account is PROPOSED. The independent partly-responsible defect sentence is AI-adjudicated ASSERTED with contribution=partial; its grammar-based scope judgement is explicit in the log. |
| Polarity / compound effects | D078 strong NH3 interaction is explicitly absent; nonresponse remains negative against base response. The positive explanation targets the explicit nonresponse outcome and contains the whole absent-interaction/current/mobility conjunction. No quantitative cancellation or independent sufficiency is inferred. |
| Identity / attachment | GO, rGO, graphene, dopants, variable stoichiometries and passivations stay distinct. Original cannot-link decisions and revision scope are retained. Conditions and units remain attached to their exact source result. |

All 23 predicates have an exact DEV example, directed endpoint constraints, qualifier constraints, polarity/modality support, contrast and group/ambiguity rules in ontology.json. Generic semantic rules are based on DEV constructions, not article-specific predicate names. New heads/ranges have direct DEV support; no DEVICE range is added to USED_FOR. HAS_MEMBER endpoint pairs are explicit, and mixed PROPERTY→PERFORMANCE membership is restricted to requirement_bundle.

Repeated canonical triples may have separate source assertions and conditions. They are counted separately from canonical triples and are not merged merely because head/relation/tail repeat. Existing IDs are retained for unchanged assertions; candidate IDs becoming accepted assertions stay traceable, and group replacements map every original candidate to the new collective assertion. Metadata-only ontology/source-context additions are not counted as semantic corrections.

No evaluation data was read by this isolated semantic designer. The parent context had prior evaluation exposure, and historical 0.3 freeze persistence was retried after calibration display. This limits end-to-end independence claims; the fresh input manifest and fixed DEV snapshot make this run inspectable but do not erase historical contamination. The original 0.3 reports are preserved unchanged.

Outstanding uncertainty is explicit: two historical D024 use candidates and one carbon-sequestration audit abstention. Independent human ontology approval and label review are still pending. No claim of perfect semantic recall, human gold or independent review is made.
'''
    (OUT/'CONSISTENCY_AUDIT.md').write_text(consistency,encoding='utf-8',newline='\n')
    changelog=f'''# Changes from the historical 0.3 baseline

Ontology v1.0 is a new DEV-only semantic specification. The old 0.3 files and freeze identity are preserved; they are not retroactively edited.

- Added CAUSES for produced events; EXPLAINS for source attribution; CHANGES_PARAMETER with required signed/unspecified direction; DEPENDS_ON for explicit variable/configuration dependence; MEETS_REQUIREMENT for a joint bundle. Total: 23 directed predicates and the same 12 entity kinds.
- Mapped INCREASES and observed decreases to CHANGES_PARAMETER; mapped DOMINATES to EXPLAINS+dominant. No standalone DOMINATES/DECREASES/INCREASES is needed. Retained all 18 useful baseline meanings, with repaired UTF-8 directions for OPTIMIZES and FACILITATES.
- Extended HAS_PROPERTY to structural MORPHOLOGY bearers and HAS_MECHANISM to MATERIAL. Added explicit group/member pairs for joint morphology/mechanism claims and mixed requirements. Declined DEVICE tails for USED_FOR where DEV wording is insufficient.
- Reannotated all 12 DEV abstracts, preserving old source/evidence offsets, unreviewed status and supported labels. Resolved 18 of 20 historical questions; 2 remain insufficient. Retained 1 additional backward-audit abstention. The historical 19/20 discrepancy is the later D078-Q9 addition, not a lost/duplicated question.
- Removed the D035 16-edge material/gas grid, the D017 unspecified mechanism linkage, D024 unsupported neutral-tuning optimality, and the inconsistent carbon-sequestration use. Recovered intermediate parameter/event chains, grouped explanation and dependence, signed D078 effects, local modality/polarity and qualifier scope.
- Added {stats['added_assertions']} assertions; retired {stats['retired_assertions']}; semantically corrected {stats['semantically_corrected_existing_assertions']} retained assertions. {stats['metadata_only_existing_assertions']} retained assertions have metadata-only changes. Final accepted assertions: {stats['final_assertions']} (baseline {stats['baseline_assertions']}); mentions: {stats['final_mentions']} (baseline {stats['baseline_mentions']}). Complete identity-level counts are in migration_summary.json.
- Separated AI design decisions, earlier user design instructions, technical freeze, final human ontology approval and human gold review. No final human approval or human label review is recorded. source_context is an AI interpretation for regressions, not external truth.
- Added machine-readable rules, full relation/entity definitions, rubric, per-question decisions, sentence coverage audit, consistency self-audit, input hashes, DEV-only source snapshots and deterministic reannotation/patch scripts. Root integration provides the final freeze/hash/commit manifest and repository validation.
'''
    (OUT/'CHANGELOG.md').write_text(changelog,encoding='utf-8',newline='\n')

if __name__=='__main__':main()
