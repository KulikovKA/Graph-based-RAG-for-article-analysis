"""Register a source-backed D004 schema gap before full annotation."""
import json
from build_dev_pair import BASE, Draft

d = Draft('D004')
d.ms('S4', '''treatment|microwave treatment of graphene–SnO 2 nanocomposites|PROCESS|microwave treatment
graphene|graphene|MATERIAL|graphene|energy_transport_promoter|2
transport|efficient transport of the microwave energy|PROCESS|microwave energy transport
evap_redeposit|evaporation and redeposition of SnO x nanoparticles|PROCESS|SnOx evaporation/redeposition process group''')
case = dict(question_id='Q3', status='UNRESOLVED', document_code=d.code,
    document_id=d.src['document_id'], revision_id=d.src['revision_id'], split='DEV',
    title=d.src['title'], category='ONTOLOGY_ENDPOINT_OR_PREDICATE_GAP',
    annotation_scope='SOURCE_CANDIDATE_ONLY_S4; NOT_A_COMPLETE_DOCUMENT_DRAFT',
    evidence=[d.sentences['S4']], context=[d.sentences['S3'], d.sentences['S5']],
    candidate_mentions=d.data['mentions'], candidate_concepts=list(d.concepts.values()),
    candidate_evidence_spans=d.data['evidence_spans'],
    candidates=[dict(head_mention_id=d.mentions[h]['mention_id'], tail_mention_id=d.mentions[t]['mention_id'],
        proposed_relation_type='FACILITATES', modality='ASSERTED', polarity='POSITIVE',
        support_status='UNRESOLVED', reason='Explicit promotion/facilitation of a process; accepted IMPROVES has no MATERIAL head or PROCESS tail.')
        for h,t in [('graphene','transport'),('treatment','evap_redeposit')]],
    human_review='NOT_REVIEWED', ontology_change_applied=False)
(BASE/'annotations/reviews/pending_source_cases.jsonl').write_text(json.dumps(case,ensure_ascii=False)+'\n',encoding='utf-8')
print('Recorded Q3 source candidates; D004 full annotation has not started.')
