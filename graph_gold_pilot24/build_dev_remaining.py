"""Source-only curated DEV records; unapproved predicates remain unresolved cases."""
from build_dev_pair import Draft


def d003():
    d = Draft('D003')
    d.ms('S1', '''analysis|accurate, continuous analysis|PROCESS|accurate continuous gas analysis|background_unmet_goal
gases|healthcare-relevant gases|ANALYTE|healthcare-relevant gases|background_analyte_class
nox|nitrogen oxides|ANALYTE|nitrogen oxides|target_analyte_class
nox_alias|NO x|ANALYTE|nitrogen oxides|target_analyte_class
humid|humid environment|OPERATING_CONDITION|humid environment
cost|low-cost|PROPERTY|low cost
stretch1|stretchable|PROPERTY|stretchability
devices|gas sensing devices|DEVICE|background low-cost stretchable gas sensors''')
    d.rel('devices', 'HAS_PROPERTY', 'cost', scope='BACKGROUND')
    d.rel('devices', 'HAS_PROPERTY', 'stretch1', scope='BACKGROUND')
    d.note('S1', 'Remains elusive describes an unmet background goal, not an explicit universally negative DETECTS claim. No achieved accuracy/continuous-analysis performance is assigned to these generic devices.')
    d.ms('S2', '''sensor|moisture-resistant, stretchable NO x gas sensor|DEVICE|study stretchable LIG NOx sensor
moist|moisture-resistant|PROPERTY|moisture resistance
stretch2|stretchable|PROPERTY|stretchability
nox2|NO x|ANALYTE|nitrogen oxides|target_analyte_class
lig|laser-induced graphene|MATERIAL|laser-induced graphene
lig_alias|LIG|MATERIAL|laser-induced graphene''')
    d.rel('sensor', 'HAS_PROPERTY', 'moist')
    d.rel('sensor', 'HAS_PROPERTY', 'stretch2')
    d.rel('sensor', 'USES_MATERIAL', 'lig')
    d.rel('sensor', 'DETECTS', 'nox2')
    d.ms('S3', '''substrate|soft elastomeric substrate|DEVICE|elastomeric substrate|support_component
soft|soft|PROPERTY|softness
elastomer|elastomeric|MATERIAL|elastomer (unspecified)|substrate_material_class
encap|moisture-resistant semipermeable encapsulant|DEVICE|semipermeable encapsulant|encapsulation_component
encap_moist|moisture-resistant|PROPERTY|moisture resistance
semi|semipermeable|PROPERTY|semipermeability
layer|LIG sensing and electrode layer|DEVICE|LIG sensing/electrode layer|dual_function_layer
lig3|LIG|MATERIAL|laser-induced graphene
tuning|tuning laser processing parameters|PROCESS|laser parameter tuning
laser|laser processing|PROCESS|laser processing
parameters|laser processing parameters|PROPERTY|laser processing parameter group
power|power|PROPERTY|laser power|fabrication_parameter
density|image density|PROPERTY|laser image density|fabrication_parameter
defocus|defocus distance|PROPERTY|laser defocus distance|fabrication_parameter''')
    d.rel('substrate', 'HAS_PROPERTY', 'soft')
    d.rel('substrate', 'USES_MATERIAL', 'elastomer')
    d.rel('encap', 'HAS_PROPERTY', 'encap_moist')
    d.rel('encap', 'HAS_PROPERTY', 'semi')
    d.rel('layer', 'USES_MATERIAL', 'lig3')
    for component in ('substrate', 'encap', 'layer'):
        qs = [('S3', 'Sandwiched between a soft elastomeric substrate and a moisture-resistant semipermeable encapsulant',
               'layer_position', 'LIG sensing/electrode layer between substrate and encapsulant', None)] if component == 'layer' else []
        d.rel('sensor', 'HAS_COMPONENT', component, sentences=['S2', 'S3'], qualifiers=qs)
    for parameter in ('power', 'density', 'defocus'):
        d.rel('parameters', 'HAS_MEMBER', parameter)
        d.rel('laser', 'HAS_PROPERTY', parameter)
    # Optimizing a device layer is explicit, but IMPROVES currently permits only
    # property/performance tails. Do not silently widen the accepted relation schema.
    d.data['unresolved'].append(dict(question_id='Q2', status='UNRESOLVED',
        category='ONTOLOGY_ENDPOINT_OR_PREDICATE_GAP', sentence_id='S3',
        head_mention_id=d.mentions['tuning']['mention_id'],
        tail_mention_id=d.mentions['layer']['mention_id'],
        proposed_relation_type='OPTIMIZES', proposed_modality='ASSERTED', proposed_polarity='POSITIVE',
        reason='Source explicitly optimizes a device layer by tuning. IMPROVES only permits PROPERTY/PERFORMANCE tails, and no optimized metric is named.',
        evidence=[d.sentences['S3']], annotation_status='UNRESOLVED',
        alternatives=['Add OPTIMIZES PROCESS -> DEVICE', 'Extend IMPROVES tails to DEVICE, retain unspecified optimized metric', 'Keep UNRESOLVED']))
    d.note('S3', 'Q2 resolved: OPTIMIZES(tuning, layer) is authorized without assigning an unspecified optimized metric. Positional sandwich information is explicit on HAS_COMPONENT(layer), without pretending between means inside either surrounding component.')
    d.ms('S4', '''sensor4|gas sensor|DEVICE|study stretchable LIG NOx sensor
lig4|needlelike LIG|MATERIAL|needlelike laser-induced graphene
needle|needlelike|MORPHOLOGY|needlelike morphology
laser4|laser processing|PROCESS|laser processing
settings|optimal laser processing parameters|PROPERTY|optimal laser processing parameters
response|large response|PERFORMANCE|gas response per concentration
no_resp|NO|ANALYTE|nitric oxide|target_analyte|-1
no2_resp|NO 2|ANALYTE|nitrogen dioxide|target_analyte|-1
lod|ultralow detection limit|PERFORMANCE|detection limit
no_lod|NO|ANALYTE|nitric oxide|target_analyte|3
no2_lod|NO 2|ANALYTE|nitrogen dioxide|target_analyte|2
speed|fast response/recovery|PERFORMANCE|response/recovery speed
selectivity|excellent selectivity|PERFORMANCE|selectivity''')
    d.rel('sensor4', 'USES_MATERIAL', 'lig4')
    d.rel('lig4', 'HAS_MORPHOLOGY', 'needle')
    d.rel('lig4', 'FABRICATED_BY', 'laser4', qualifiers=[('S4', 'optimal laser processing parameters', 'parameter_selection', 'optimal (values unspecified)', None)])
    for analyte, raw, value in [('no_resp', '4.18‰ ppm −1 to NO', 4.18), ('no2_resp', '6.66‰ ppm −1 to NO 2', 6.66)]:
        d.rel('sensor4', 'DETECTS', analyte, qualifiers=[('S4', raw, 'response_per_concentration', value, '‰ ppm −1')])
    # Separate performance assertions preserve analyte/value attachment even though
    # both refer to the same response mention and canonical metric.
    d.rel('sensor4', 'HAS_PERFORMANCE', 'response', qualifiers=[
        ('S4', '4.18‰ ppm −1 to NO', 'NO_response_per_concentration', 4.18, '‰ ppm −1'),
        ('S4', '6.66‰ ppm −1 to NO 2', 'NO2_response_per_concentration', 6.66, '‰ ppm −1')])
    d.rel('sensor4', 'HAS_PERFORMANCE', 'lod', qualifiers=[
        ('S4', '8.3 ppb to NO', 'NO_detection_limit', 8.3, 'ppb'),
        ('S4', '4.0 ppb to NO 2', 'NO2_detection_limit', 4.0, 'ppb')])
    d.rel('sensor4', 'HAS_PERFORMANCE', 'speed')
    d.rel('sensor4', 'HAS_PERFORMANCE', 'selectivity', note='No numerical response/recovery time or named comparison analyte is given.')
    d.ms('S5', '''design|design of a stretchable serpentine structure|PROCESS|serpentine structure design
mechanism5|design of a stretchable serpentine structure in the LIG electrode and strain isolation from the stiff island|MECHANISM|combined serpentine design and strain isolation
serpentine|stretchable serpentine structure|MORPHOLOGY|stretchable serpentine structure
electrode|LIG electrode|DEVICE|LIG electrode
lig5|LIG|MATERIAL|laser-induced graphene
isolation|strain isolation|MECHANISM|strain isolation
island|stiff island|DEVICE|stiff island|mechanical_isolation_component
stiff|stiff|PROPERTY|stiffness
sensor5|gas sensor|DEVICE|study stretchable LIG NOx sensor
stretch5|stretched by 30%|PERFORMANCE|demonstrated stretching capability''')
    d.rel('electrode', 'USES_MATERIAL', 'lig5')
    d.rel('electrode', 'HAS_MORPHOLOGY', 'serpentine')
    d.rel('island', 'HAS_PROPERTY', 'stiff')
    d.rel('sensor5', 'HAS_PERFORMANCE', 'stretch5', qualifiers=[('S5', '30%', 'stretch', 30, '%')])
    d.rel('sensor5', 'HAS_MECHANISM', 'mechanism5', qualifiers=[('S5', 'stretched by 30%', 'explained_capability', 'stretching by 30%', None)], note='Mechanical explanation for stretchability, not a proposed gas-response mechanism; design and isolation are collective.')
    d.rel('mechanism5', 'MECHANISM_INVOLVES', 'design')
    d.rel('mechanism5', 'MECHANISM_INVOLVES', 'serpentine')
    d.rel('mechanism5', 'MECHANISM_INVOLVES', 'isolation', qualifiers=[('S5', 'from the stiff island', 'isolation_reference', 'stiff island', None)])
    d.note('S5', 'The 30% stretching capability is explained jointly by serpentine design and strain isolation. HAS_MECHANISM includes the explicit explained_capability qualifier; no claim that each mechanism alone achieves 30%.')
    d.ms('S6', '''moist6|moisture-resistant property|PROPERTY|moisture resistance
rh|relative humidity of 90%|OPERATING_CONDITION|relative humidity 90%
sensor6|gas sensor|DEVICE|study stretchable LIG NOx sensor
monitor|monitor the personal local environment|APPLICATION|personal local environmental monitoring
time|different times of the day|OPERATING_CONDITION|different times of day
breath|analyze human breath samples|APPLICATION|human breath analysis
samples|human breath samples|ANALYTE|human breath samples|sample_matrix
classify|classify patients with respiratory diseases from healthy volunteers|APPLICATION|classification of respiratory-disease patients versus healthy volunteers
disease|respiratory diseases|OTHER|respiratory diseases|clinical_target
healthy|healthy volunteers|OTHER|healthy volunteers|comparison_population''')
    d.rel('sensor6', 'HAS_PROPERTY', 'moist6', qualifiers=[('S6', 'relative humidity of 90%', 'relative_humidity', 90, '%')])
    d.rel('sensor6', 'USED_FOR', 'monitor', qualifiers=[('S6', 'different times of the day', 'monitoring_times', 'different times of day', None)])
    d.rel('sensor6', 'USED_FOR', 'breath')
    d.rel('sensor6', 'USED_FOR', 'classify', note='Reported demonstration, not clinical diagnostic accuracy. No diagnostic sensitivity/specificity is supplied.')
    d.ms('S7', '''sensor7|Moisture-resistant, stretchable NO x gas sensors|DEVICE|study stretchable LIG NOx sensor
moist7|Moisture-resistant|PROPERTY|moisture resistance
stretch7|stretchable|PROPERTY|stretchability
nox7|NO x|ANALYTE|nitrogen oxides|target_analyte_class
wearables|wearable devices|DEVICE|wearable devices|prospective_device_class
biomarkers|biomarkers|ANALYTE|biomarkers (unspecified)|prospective_target_class
environments|exposed environments|OTHER|exposed environments|prospective_sampling_context
diagnostics|early disease diagnostics|APPLICATION|early disease diagnostics''')
    d.rel('sensor7', 'HAS_PROPERTY', 'moist7')
    d.rel('sensor7', 'HAS_PROPERTY', 'stretch7')
    d.rel('sensor7', 'USED_FOR', 'diagnostics', modality='HYPOTHETICAL', scope='OUTLOOK')
    d.rel('wearables', 'DETECTS', 'biomarkers', modality='HYPOTHETICAL', scope='OUTLOOK', note='Prospective capability, not demonstrated detection of every biomarker or confirmed diagnosis.')
    d.same(['sensor', 'sensor4', 'sensor5', 'sensor6', 'sensor7'], 'Repeated study gas sensor/platform; source scopes and configurations remain local.', coref=True)
    d.same(['lig', 'lig_alias', 'lig3', 'lig5'], 'Explicit laser-induced graphene (LIG) definition and repeated acronym.')
    d.identity('lig', 'lig4', 'BROADER', 'Needlelike LIG specifies morphology; generic LIG is not narrowed everywhere.')
    d.same(['nox', 'nox_alias', 'nox2', 'nox7'], 'Explicit nitrogen oxides (NOx) definition; remains a family, not specifically NO2.')
    d.same(['no_resp', 'no_lod'], 'Repeated NO formula in analyte-specific response/LOD values.')
    d.same(['no2_resp', 'no2_lod'], 'Repeated NO2 formula; not NO.')
    d.identity('no_resp', 'no2_resp', 'DIFFERENT', 'Explicit separate response and detection-limit entries for NO and NO2.')
    d.identity('nox', 'no_resp', 'BROADER', 'NO is one of the named targets of this NOx device; the family is not collapsed into one target.')
    d.identity('nox', 'no2_resp', 'BROADER', 'NO2 is one of the named targets of this NOx device; the family is not collapsed into one target.')
    d.same(['stretch1', 'stretch2', 'stretch7'], 'Same stretchability property concept; the background and study devices remain distinct.')
    d.same(['moist', 'encap_moist', 'moist6', 'moist7'], 'Same moisture-resistance property; device versus encapsulant bearer and RH qualifier remain separate.')
    d.same(['laser', 'laser4'], 'Same laser-processing concept; tuning parameters are not merged into the process.')
    d.data['unresolved'] = []
    d.rel('tuning', 'OPTIMIZES', 'layer')
    d.data['exhaustive_relations'] = True
    d.data['completeness_status'] = 'AI_FIRST_PASS_ALL_SENTENCES; HUMAN_RECALL_REVIEW_PENDING'
    d.data['review']['adjudication_status'] = 'SCHEMA_Q1_Q2_Q3_RESOLVED_ANNOTATIONS_NOT_REVIEWED'
    d.save()


if __name__ == '__main__':
    d003()
