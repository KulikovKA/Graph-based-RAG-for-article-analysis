"""Apply the fixed, approved v1.0 ontology to the six CALIBRATION sources."""
from common import Review


def D018():
    r=Review('D018','CALIBRATION')
    r.add_m('transition_event','S3','transition of growth mechanism from conventional ion-by-ion growth to particle-mediated crystallization','PROCESS','growth mechanism transition from ion-by-ion to particle-mediated crystallization')
    a=r.add_a('agglomeration','CAUSES','transition_event',reason='Leading to explicitly produces a transition event; original growth mechanisms are not cause/effect objects.')
    r.decide('D018-Q4','MAP_TO_EXISTING','Reify the exact transition event and preserve the explicitly stated agglomeration trigger with CAUSES. Its from/to wording remains in the event span.',[a])
    a=r.add_a('meso2','HAS_MECHANISM','mechanisms',reason='Frozen v1.0 admits MATERIAL bearers; this source explicitly supplies the formation account.')
    r.decide('D018-Q5','MAP_TO_EXISTING','MATERIAL -> MECHANISM is already permitted in approved v1.0.',[a])
    r.decide('D018-Q6','UNSUPPORTED_FROZEN_ONTOLOGY','Kinetic control has a MORPHOLOGY target. Do not retype the architecture as a property or expand CHANGES_PARAMETER/OPTIMIZES endpoints.')
    a=r.a('ripening','FACILITATES','growth');a['relation_type']='EXPLAINS'
    r.changes.append(dict(action='CORRECT_PREDICATE',assertion_id=a['assertion_id'],reason='Responsible for attributes growth to ripening; use EXPLAINS without strengthening to direct event production.'))
    for key in ['agglomeration','evolution','transformation','ripening','growth','organization','reduction']:
        r.add_a('mechanisms','MECHANISM_INVOLVES',key,reason='The enumerated source formation account explicitly includes this process.')
    r.add_m('explanatory_group','S6','high specific surface area and improved conductivity','PROPERTY','surface-area and conductivity explanatory group','explicit_group')
    for key in ['area','conductivity']:r.add_a('explanatory_group','HAS_MEMBER',key)
    r.add_a('explanatory_group','EXPLAINS','sensitivity',mode='COMPARED',qualifiers=[('S6','high specific surface area and improved conductivity','scope','collective',None)],reason='Owing to explicitly attributes the comparative sensitivity jointly to the two features.')
    r.a('super','FABRICATED_BY','attachment')['modality']='ASSERTED'
    r.qualifiers({'synthesis_conditions':'scope_limit','reagents':'scope_limit','condition':'scope_limit','sequence_stage':'scope_limit','temporal_relation':'scope_limit','cooccurring_process':'scope_limit'},redundant=['source_causal_wording','support_basis'])
    r.abstain('TEMPORAL_RELATION_NOT_IN_FROZEN_V1','Simultaneous organization and GO reduction are retained as exact source/context; v1 has no dedicated temporal relation.',[r.se('S3')])
    r.note('S3','Reviewed the full three-stage account: event production, growth explanation, material mechanism and involved processes. Temporal simultaneity is not a new predicate.')
    r.note('S4','The source asserts inferred formation (are also formed, judging from observed polyhedrons); evidential inference alone is not PROPOSED modality.')
    r.note('S5','Kinetic control of structure stays an abstention under unchanged endpoints.')
    r.note('S6','One collective explanation preserves both features, comparator and room temperature; no sensitivity number is supplied.')
    return r.finish()


def D050():
    r=Review('D050','CALIBRATION')
    for qid,h,t in [('D050-Q4','reduced','transition'),('D050-Q5','hybrid3','weak')]:
        a=r.add_a(h,'HAS_MECHANISM',t,reason='Observed material N-P behavior is permitted by the fixed material mechanism domain.')
        r.decide(qid,'MAP_TO_EXISTING','MATERIAL -> MECHANISM already exists in v1.0.',[a])
    r.decide('D050-Q6','UNSUPPORTED_FROZEN_ONTOLOGY','The stated explanatory factor is PERFORMANCE, which is not an EXPLAINS head. Preserve attribution without retyping the factor.')
    a=r.add_a('flex5','EXPLAINS','stable',qualifiers=[('S5','extreme bending stress','scope_limit',None,None)],reason='Flexibility explicitly ensures stability under bending; PROPERTY -> PERFORMANCE is permitted.')
    r.decide('D050-Q7','MAP_TO_EXISTING','The source-supported property explanation is covered by fixed v1.0.',[a])
    r.qualifiers({'exposure_stage':'scope_limit','mechanical_condition':'scope_limit'})
    r.note('S2','Negligible response is a low positive magnitude, not explicit non-detection; initial injection is local scope.')
    r.note('S3','20 micrometre CNT length remains literal in the property mention/evidence. A normalized length qualifier is not in v1 and is separately abstained, not replaced by width.')
    r.note('S4','PERFORMANCE -> PERFORMANCE explanatory attribution remains unsupported; no artificial property retyping.')
    r.note('S5','Property explanation and performance stability retain the exact bending condition.')
    return r.finish()


def D029():
    r=Review('D029','CALIBRATION')
    a=r.add_a('homogeneity','EXPLAINS','sensitivity5',mode='PROPOSED',reason='The source identifies a design factor for the goal of maximizing sensitivity; no numerical realized gain is asserted.')
    r.decide('D029-Q4','MAP_TO_EXISTING','Use existing PROPERTY -> PERFORMANCE explanation with prospective design-goal modality.',[a])
    r.add_a('printing','FACILITATES','deposit',scope='BACKGROUND',reason='Allowing explicitly describes the deposition enabled by inkjet printing.')
    r.qualifiers({'tested_stimuli':'analyte_scope','deposition_substrate':'material_configuration'})
    r.note('S1','Market requirements remain goals, distinct from graphene intrinsic properties and actual sensor measurements.')
    r.note('S4','Characterized response towards three stimuli is not invented successful detection for each stimulus.')
    r.note('S5','Thickness tuning and homogeneity concern the maximize-sensitivity design goal; no optimum thickness or numeric gain is inferred.')
    return r.finish()


def D042():
    r=Review('D042','CALIBRATION')
    a=r.add_a('passivate','CHANGES_PARAMETER','parameters',polarity='NEGATIVE',sentences=['S2','S3'],qualifiers=[('S3','no significant changes','direction','unspecified',None),('S3','significant','strength',None,None),('S3','CO and CO2','analyte_scope',None,None),('S3','H-AGNR and N-AGNR','material_configuration',None,None)],reason='No significant changes negates significant parameter change, not all adsorption or every arbitrarily small effect.')
    r.decide('D042-Q4','MAP_TO_EXISTING','Signed-change ontology supports explicit negative significant-change scope. No mathematically exact unchanged value is inferred.',[a])
    r.decide('D042-QENERGY','INSUFFICIENT_EVIDENCE','Keep the source 9x/13x wording; signed energy versus binding magnitude is not resolved and no absolute energy is derived.')
    for a in r.d['assertions']:
        for q in a['qualifiers']:
            if q['qualifier_type']=='computational_tool':
                q.update(qualifier_type='evidence_basis',raw_value='calculation',unit=None)
    r.qualifiers({'passivant':'material_configuration','analyte':'analyte_scope','relative_energy':'comparison'})
    r.m('materials')['contextual_role']='explicit_group'
    for key in ['h','n','pth','ptn']:
        r.add_a('materials','HAS_MEMBER',key,reason='The four modeled systems are explicitly identified across the initial and Pt-doped system descriptions; no material-by-gas Cartesian grid is inferred.')
    for a in r.d['assertions']:
        if not any(q['qualifier_type']=='evidence_basis' for q in a['qualifiers']):
            r.attach(a,'S1','built using Atomistic ToolKit Virtual NanoLab (ATK-VNL)','evidence_basis','calculation')
    r.note('S1','The four systems are computational models; source tool is evidence_basis=calculation, not a physical synthesis tool.')
    r.note('S3','No significant change remains a negative scoped effect; no blanket no sensing claim.')
    r.note('S4','All four signed energies, respectively mapping and eV units remain in original source and unresolved metric-qualifier candidates. v1 lacks a generic adsorption-energy qualifier; none is added or renamed to an unrelated barrier metric.')
    r.note('S6','Literal almost-nine-times comparisons are preserved without new absolute energies or an assumed signed-value convention.')
    r.note('S7','Literal almost-thirteen-times comparison and its CO/Pt-H configuration stay distinct from the other three cases.')
    return r.finish()


def D021():
    r=Review('D021','CALIBRATION')
    a=r.add_a('synthesis','CHANGES_PARAMETER','properties',qualifiers=[('S3','affects','direction','unspecified',None)],reason='Affects states a parameter effect without improvement or known sign.')
    r.decide('D021-Q4','MAP_TO_EXISTING','Use the existing unspecified signed-parameter effect; no IMPROVES or new AFFECTS relation.',[a])
    for a in r.d['assertions']:
        if a['relation_type']=='USED_FOR' and r.m('gasbarrier')['mention_id']==a['tail_mention_id'] or a['relation_type']=='USED_FOR' and r.m('separation')['mention_id']==a['tail_mention_id']:
            a['modality']='HYPOTHETICAL'
    r.retire('polymer','FABRICATED_BY','production','Discussion of outlook and industrial-scale challenges does not identify a fabrication method or establish deployment; retain as review discourse, not a technical fabrication fact.')
    r.qualifiers()
    r.note('S2','Opened new possibilities is prospective application modality; GO and rGO remain chemically distinct.')
    r.note('S3','Unspecified property effect uses CHANGES_PARAMETER with required direction=unspecified.')
    r.note('S5','Industrial-scale outlook/challenges are a discourse exclusion; no completed production or unnamed fabrication method is inferred.')
    return r.finish()


def D093():
    r=Review('D093','CALIBRATION')
    a=r.add_a('waveguide','USES_MATERIAL','film',scope='REVIEW_BACKGROUND',reason='Explicit incorporation of the material into optical waveguides supports the inverse material-use construction; no MATERIAL-headed INTEGRATED_IN extension.')
    r.decide('D093-Q4','MAP_TO_EXISTING','Represent the explicit incorporated material using DEVICE -> MATERIAL, without retyping graphene as DEVICE.',[a])
    r.add_m('integration_process','S2','incorporated with optical waveguides','PROCESS','graphene incorporation with optical waveguides')
    r.add_a('two','EXPLAINS','integration_process',scope='REVIEW_BACKGROUND',reason='Benefiting from its two-dimensional nature explicitly links this structure to the integration process.')
    for predicate,key in [('HAS_MECHANISM','principles'),('HAS_PROPERTY','properties'),('FABRICATED_BY','fabrication'),('USED_FOR','implementation')]:
        r.retire('micro',predicate,key,'This is an enumeration of review topics, without a named mechanism/property/fabrication technique or concrete implementation claim. Preserve mentions and sentence evidence as discourse.')
    r.qualifiers()
    r.abstain('EXPLANATION_RANGE_NOT_IN_FROZEN_V1','Photoelectric characteristics explain use across application fields, but EXPLAINS does not admit APPLICATION tails. The uses and property remain separately supported; no range extension.',[r.se('S1')])
    r.note('S1','Preserve field-level applications and property separately; their explanatory link to APPLICATION is an explicit abstention.')
    r.note('S2','Material incorporation maps to waveguide USES_MATERIAL film. Structure explains the source-expressed integration process; no exact atomic-layer number is invented.')
    r.note('S4','Review-topic enumeration is excluded from factual device-specific mechanisms, properties, techniques and implementation links.')
    return r.finish()


if __name__=='__main__':
    for f in [D018,D050,D029,D042,D021,D093]:f()
