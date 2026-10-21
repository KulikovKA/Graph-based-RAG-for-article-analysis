"""Build the DEV-only semantic specification. No evaluation inputs are read.

Run migrate_dev.py for deterministic snapshots, adjudications, revisions and audits.
"""
from __future__ import annotations

import json
from collections import defaultdict

ONTOLOGY_ID = 'pilot24-ontology-v1.0'

ENTITIES = {
    'MATERIAL': ('A substance, composition, or material system considered as matter.', 'graphene; graphene oxide; reduced graphene oxide; Ti3C2Tx MXene', 'A fabricated sensor or functional component is DEVICE; a material may FUNCTIONS_AS a device component without becoming identical to it.', 'Preserve composition, oxidation, dopant and defect distinctions; expand locally defined aliases only.'),
    'DEVICE': ('An engineered object or functional physical component with a technical role.', 'gas sensor; electrode; sensing layer; membrane', 'A pore, junction or electronic layer described as structure is MORPHOLOGY; a manufactured electrode layer is DEVICE.', 'Separate device class from source-scoped configuration and experimental instance.'),
    'PROPERTY': ('A physical, chemical, structural or manufacturing attribute or parameter of a bearer.', 'hole concentration; oxygen atomic ratio; adsorption energy; noise; pore width', 'Sensitivity, selectivity, detection limit and task response are PERFORMANCE; a geometric structure is MORPHOLOGY.', 'Keep parameter identity distinct from value, direction of change, condition and bearer instance.'),
    'PERFORMANCE': ('A capability, task outcome or evaluation measure in an application.', 'sensitivity; selectivity; response; detection limit; sensing stability', 'Physical conductivity, carrier concentration and noise are PROPERTY even when they explain performance.', 'Do not identify measurements across different analytes, configurations or conditions; retain those attachments.'),
    'ANALYTE': ('A substance or explicit substance class in the contextual role of target, adsorbate or comparison gas.', 'NH3 target; NO2 target; comparison gases/VOCs', 'NO2 used as dopant in D060 is MATERIAL; do not turn a generic gas mention into a specific chemical.', 'Role-specific mention kind does not assert a different chemical species; no SAME link between different compounds.'),
    'PROCESS': ('A technical action, transformation, operation or event, including formation and measurement.', 'microwave treatment; adsorption; junction formation; n-doping', 'MECHANISM describes how or why a phenomenon occurs; the event it involves remains PROCESS.', 'Keep the event of formation distinct from the resulting object and from a named method family.'),
    'MECHANISM': ('A source-expressed explanation, interaction, or combined explanatory account of technical behavior.', 'electrostatic interaction; sensing mechanism; combined current and mobility effects', 'A junction itself is MORPHOLOGY; formation is PROCESS; do not promote every process into an explanation.', 'Preserve the scope of hypothesized accounts and joint explanations; no inferred quantitative cancellation.'),
    'OPERATING_CONDITION': ('An environmental, sample or operating circumstance under which a claim applies.', '150 °C; room temperature; gas mixture with reducing gases', 'A measured outcome is PROPERTY/PERFORMANCE. A laser setting can be PROPERTY of a process.', 'Normalize only explicit, unambiguous units and retain original values; room temperature is not silently 25 °C.'),
    'MORPHOLOGY': ('A structural arrangement, shape, geometry or electronic/spatial feature.', 'heterojunction; pore; electron accumulation/depletion layer; charged impurities', 'Material composition is MATERIAL; engineered sensing/electrode components are DEVICE; carrier concentration is PROPERTY.', 'Preserve junction composition, pore passivation, electronic layer type and location; never equate interfaces with their formation.'),
    'TECHNOLOGY': ('A named technology or method family referenced as an approach.', 'density functional theory; electron-beam technology', 'A concrete execution or transformation is PROCESS; a technical end use is APPLICATION.', 'A source may name a method family and an execution separately; RELATED does not imply SAME.'),
    'APPLICATION': ('An explicitly named end use, task or application field.', 'gas separation; breath analysis; gas sensing; disease diagnostics', 'A device class such as fuel cell remains DEVICE; vague impact on it does not by itself establish USED_FOR.', 'Preserve application scope and prospective modality; do not turn discussion of a field into a fabricated device.'),
    'OTHER': ('A source-expressed technical referent that does not fit the other kinds.', 'clothes as receiving host; functional template role', 'Use only after checking the specific kinds; contextual_role can mark a role or group without adding a new kind.', 'Keep source-scoped identity; OTHER is not permission to relax relation domains.'),
}

# Definition, direction, head kinds, tail kinds, contrast, nearest semantic distinction.
RELATIONS = {
 'HAS_PROPERTY': ('The bearer has the stated non-task physical, chemical, structural or process attribute.', 'bearer -> property', ['DEVICE','MATERIAL','PROCESS','OTHER','MORPHOLOGY'], ['PROPERTY'], 'Hole concentration belongs here; sensitivity belongs under HAS_PERFORMANCE. An increase in concentration also needs CHANGES_PARAMETER.', 'HAS_PERFORMANCE measures task outcomes; DEPENDS_ON relates a dependent quantity to its explanatory variable.'),
 'HAS_PERFORMANCE': ('The bearer exhibits the stated task capability, measured outcome or performance limitation.', 'bearer -> performance', ['DEVICE','MATERIAL'], ['PERFORMANCE'], 'D060 hole concentration is a physical parameter, not performance. D078 nonresponse is a negative response claim, not absence of a physical component.', 'HAS_PROPERTY describes intrinsic/operational attributes; performance comparisons keep their comparator and modality.'),
 'HAS_MORPHOLOGY': ('The bearer has a stated structural, geometric or electronic arrangement.', 'bearer -> structure', ['DEVICE','MATERIAL'], ['MORPHOLOGY'], 'A junction is a structure; its formation is an event. Physical material constituents use HAS_COMPONENT.', 'HAS_COMPONENT is physical composition; MORPHOLOGY includes electronic interfaces and spatial organization.'),
 'HAS_COMPONENT': ('The composite or device explicitly contains the physical material or functional component.', 'whole -> physical component', ['DEVICE','MATERIAL'], ['DEVICE','MATERIAL'], 'A list of seven candidate nanocomposites is a group with HAS_MEMBER, not seven physical parts of one nanocomposite.', 'HAS_MEMBER is enumerated membership; USES_MATERIAL records the device/material role without requiring part identity.'),
 'HAS_MEMBER': ('An explicitly expressed collection has the listed member; this does not distribute the collection claim to its members.', 'explicit group -> member', ['PROPERTY','PROCESS','MATERIAL','ANALYTE','MORPHOLOGY','MECHANISM'], ['PROPERTY','PERFORMANCE','PROCESS','MATERIAL','ANALYTE','MORPHOLOGY','MECHANISM'], 'D026 failure to meet all requirements cannot be converted to failure of each requirement. A composite is not a list of alternatives.', 'HAS_COMPONENT is physical parthood. Membership never licenses a Cartesian product of relations between two lists.'),
 'USES_MATERIAL': ('A device explicitly employs a material in its construction or functioning.', 'device -> material', ['DEVICE'], ['MATERIAL'], 'NO2 used to dope a sensor is not automatically an analyte detected by it.', 'FUNCTIONS_AS links material to a functional component role; HAS_COMPONENT records explicit physical composition.'),
 'FUNCTIONS_AS': ('A material explicitly serves as the named functional component or role.', 'material -> functional component/role', ['MATERIAL'], ['DEVICE','OTHER'], 'Porous graphene functioning as a membrane does not make the material concept identical to every membrane.', 'USED_FOR links to an end use; FUNCTIONS_AS names what the material serves as.'),
 'DETECTS': ('The sensor has an explicitly stated detection capability for the target substance, including explicit nonresponse and prospective capability.', 'sensor -> target analyte', ['DEVICE'], ['ANALYTE'], 'Selectivity over SO2 does not establish detection of SO2; a dopant is not automatically a detected gas.', 'USED_FOR describes an end use; DETECTS requires a target and a detection claim.'),
 'USED_FOR': ('The object has an explicitly stated actual, proposed or hypothetical application, process use or material sensing target.', 'object -> stated use', ['DEVICE','MATERIAL'], ['APPLICATION','PROCESS','ANALYTE'], 'D024 a pore could have impact on fuel cells does not establish porous graphene USED_FOR a fabricated fuel cell.', 'FUNCTIONS_AS names the component role; DETECTS is sensor capability; topic mention and vague impact are insufficient.'),
 'FABRICATED_BY': ('The object is obtained by the stated fabrication process, within the source modality.', 'fabricated object -> fabrication process', ['DEVICE','MATERIAL'], ['PROCESS'], 'A characterization process acting on a product is not its fabrication method.', 'ACTS_ON relates process to object; FABRICATED_BY asserts production of that object.'),
 'IMPROVES': ('The process is stated to make a property or task outcome better in the source-defined evaluative sense.', 'process -> improved property/performance', ['PROCESS'], ['PROPERTY','PERFORMANCE'], 'Increasing hole concentration is a direction of physical change, not inherently an improvement; decreasing detection limit can be an improvement.', 'CHANGES_PARAMETER has a signed or unspecified physical change; OPTIMIZES is adjustment of an object/configuration.'),
 'ACTS_ON': ('The process explicitly acts on, characterizes, transforms or otherwise operates on the object.', 'process -> affected/studied object', ['PROCESS'], ['DEVICE','MATERIAL'], 'DFT study of a group of surfaces and gases does not justify sixteen separate sensing-use claims.', 'FABRICATED_BY asserts object production; ACTS_ON does not imply an improved or fabricated outcome.'),
 'INTEGRATED_IN': ('The functional object is explicitly incorporated into the receiving host.', 'integrated object -> host', ['DEVICE'], ['DEVICE','OTHER'], 'A material merely proposed for an application is not already integrated into that device.', 'HAS_COMPONENT gives whole-to-part direction; INTEGRATED_IN gives inserted-object-to-host direction.'),
 'HAS_MECHANISM': ('The device or material has the stated source-expressed mechanism for its specified behavior.', 'device/material bearer -> mechanism', ['DEVICE','MATERIAL'], ['MECHANISM'], 'The mechanism explains behavior; it is not a material constituent. An absent interaction with NH3 must keep NEGATIVE polarity and its target scope.', 'EXPLAINS links explanatory factor to an outcome, while HAS_MECHANISM links bearer to its explanatory account.'),
 'MECHANISM_INVOLVES': ('The mechanism explicitly involves the named subordinate mechanism, process or structure.', 'mechanism -> involved mechanism/event/structure', ['MECHANISM'], ['MECHANISM','PROCESS','MORPHOLOGY'], 'Electron accumulation layer is a structure involved in the mechanism; the layer is not the complete sensing mechanism.', 'HAS_COMPONENT is physical parthood; CAUSES asserts production and is stronger than mere involvement.'),
 'LOCATED_IN': ('The electronic or geometric structure is explicitly situated in the named material.', 'structure -> containing material', ['MORPHOLOGY'], ['MATERIAL'], 'The electron depletion layer in p-type Ti3C2Tx is not located in GO/CuO/ZnO; preserve the attachment in D010.', 'HAS_MORPHOLOGY is bearer-to-structure and does not by itself encode the stated specific location.'),
 'OPTIMIZES': ('A process explicitly adjusts an object or configuration described as optimized or optimal for a stated technical objective.', 'adjustment process -> optimized object', ['PROCESS'], ['DEVICE','MATERIAL'], 'D024 tuning selectivity and diffusivity does not establish an optimum; it uses CHANGES_PARAMETER with unspecified direction.', 'IMPROVES targets a better attribute; neutral tuning is CHANGES_PARAMETER, and optimization must be explicit.'),
 'FACILITATES': ('A material or process promotes or enables the named process without asserting strict production of its outcome.', 'facilitating material/process -> facilitated process', ['MATERIAL','PROCESS'], ['PROCESS'], 'D004 graphene promotes microwave-energy transport, while microwave treatment facilitates evaporation/redeposition. Do not infer a direct graphene-to-evaporation edge.', 'CAUSES asserts that an event produces another event; EXPLAINS attributes behavior to a factor.'),
 'CAUSES': ('A source explicitly states that the causal factor produces or induces the named technical event; event endpoints remain events.', 'causal factor -> produced event', ['PROCESS','MECHANISM','MATERIAL'], ['PROCESS'], 'D004 results in formation licenses CAUSES with PROPOSED modality. Merely promoting transport uses FACILITATES. A junction object cannot replace its formation event.', 'EXPLAINS attributes an outcome to a factor; signed parameter effects use CHANGES_PARAMETER when no separate produced event is needed.'),
 'EXPLAINS': ('The source attributes an observed or proposed technical outcome or process to the explanatory factor, with the stated contribution and scope.', 'explanatory factor -> explained outcome/process', ['PROCESS','MECHANISM','MORPHOLOGY','PROPERTY'], ['PERFORMANCE','PROPERTY','PROCESS'], 'A device possessing a mechanism is HAS_MECHANISM. Three junctions jointly responsible for sensitivity do not license independent, sufficient explanations by each junction.', 'CAUSES is event production; FACILITATES is enabling; EXPLAINS preserves attribution, partial contribution and dominant background explanation.'),
 'CHANGES_PARAMETER': ('A factor changes or explicitly leaves unchanged the target physical/property or performance parameter; direction describes that parameter, not desirability.', 'changing factor -> affected parameter', ['PROCESS','MORPHOLOGY','MECHANISM'], ['PROPERTY','PERFORMANCE'], 'Increasing the magnitude of current decrease means direction=increase on the decrease magnitude; it must not become an increase in electric current.', 'IMPROVES is evaluative. Signed increases/decreases share one predicate; unspecified direction is valid only for an explicit change/tune statement.'),
 'DEPENDS_ON': ('The source explicitly states that the head quantity/outcome depends on the tail parameter or structural configuration; no functional law is inferred.', 'dependent quantity/outcome -> determining variable/configuration', ['PROPERTY','PERFORMANCE'], ['PROPERTY','MORPHOLOGY'], 'Having a pore width is HAS_PROPERTY; depending on its width is DEPENDS_ON. Joint lists do not justify a four-edge Cartesian product.', 'HAS_PROPERTY is possession; EXPLAINS is attribution of an outcome; dependence does not establish the sign, causality or quantitative law.'),
 'MEETS_REQUIREMENT': ('The material/device meets, or explicitly fails to meet, a jointly specified requirement bundle.', 'evaluated bearer -> explicit joint requirement bundle', ['MATERIAL','DEVICE'], ['PROPERTY'], 'Cannot simultaneously meet low noise AND strong signal means NOT(all requirements), not NOT(noise) AND NOT(signal).', 'HAS_PROPERTY/HAS_PERFORMANCE describe attributes individually; this relation preserves the conjunction and its negation.'),
}

QUALIFIER_DEFINITIONS = {
 'duration':'Duration attached to the stated stability or durability result.',
 'detection_limit':'Detection limit for the target/configuration of this assertion.',
 'estimation_status':'Whether the quantity is explicitly theoretical or otherwise estimated.',
 'temperature':'Explicit operating temperature or the literal room-temperature condition.',
 'bending_cycles':'Number of bending cycles for the stated deformation tolerance.',
 'twisting_cycles':'Number of twisting cycles for the stated deformation tolerance.',
 'strain':'Strain percentage for the stated deformation or strain-strength result.',
 'layer_position':'Explicit spatial arrangement of the layer relative to its named hosts.',
 'parameter_selection':'Explicit selection of optimal fabrication parameters; no missing values are inferred.',
 'response_per_concentration':'Response per target concentration, preserving literal compound units.',
 'NO_response_per_concentration':'Response slope specifically for NO.',
 'NO2_response_per_concentration':'Response slope specifically for NO2.',
 'NO_detection_limit':'Detection limit specifically for NO.',
 'NO2_detection_limit':'Detection limit specifically for NO2.',
 'stretch':'Percentage stretch for the stated stretchability capability.',
 'explained_capability':'Source-stated capability that a bearer mechanism accounts for.',
 'isolation_reference':'Object from which strain is isolated.',
 'relative_humidity':'Relative humidity condition of the stated property/capability.',
 'monitoring_times':'Source-stated temporal scope of monitoring.',
 'equipment':'Explicit fabrication or processing equipment.',
 'location':'Source-stated component placement.',
 'trend':'Source-stated noncausal trend in a bearer attribute; not a causal factor.',
 'associated_change':'An associated event retained without upgrading correlation to causality.',
 'response':'Numerical sensor response, preserving its source unit or absent unit.',
 'analyte_concentration':'Target concentration for this specific response/detection assertion.',
 'temperature_selection':'Whether an operating temperature was explicitly optimized.',
 'comparison':'Exact comparator or comparison construction; no unspecified control is invented.',
 'mass_ratio':'Ordered composition mass ratio; order follows the named material components.',
 'optimization_status':'Explicit optimal/optimized status of the stated configuration.',
 'relative_humidity_range':'Range of relative humidity for the stated behavior.',
 'coefficient_of_determination':'The source-stated R squared statistic.',
 'selectivity_comparison':'Target and comparison substances for selectivity.',
 'dopant':'Material used as dopant; it is not automatically the analyte.',
 'improvement_factor':'Source-stated amount/factor of improvement, with approximation retained.',
 'doped_detection_limit':'Detection limit in the doped configuration.',
 'undoped_detection_limit':'Detection limit in the undoped/before-doping configuration.',
 'support_method':'Source-stated computational/experimental support; it does not itself lower modality.',
 'analyte_scope':'The target substance(s) to which the assertion is restricted.',
 'material_configuration':'Source-stated material/device configuration for this assertion.',
 'concentration_regime':'Literal qualitative or quantitative concentration regime.',
 'sample_condition':'Composition or setting of the gas sample.',
 'epistemic_basis':'Calculated versus experimental provenance, separate from assertion modality.',
 'change':'Explicit qualitative property change and comparison; sign may be unspecified.',
 'study_method':'Method used to investigate the statement; not proof of actual sensor deployment.',
 'relative_sensitivity':'Sensitivity advantage relative to the named comparison.',
 'scope_limit':'Explicit restriction such as in some cases; prevents universalizing a review claim.',
 'process_location':'Material/site on which the process occurs.',
 'comparison_direction':'Literal direction of a stated comparison.',
 'comparison_material':'Material used as the comparison baseline.',
 'detection_limit_range':'Range for the stated detection limit, not a single interpolated value.',
 'SNR_ratio':'Source-stated SNR advantage, including order-of-magnitude language.',
 'selectivity_order':'Literal order-of-magnitude selectivity; original notation retained.',
 'gas_pair':'Ordered gas pair for separation selectivity.',
 'pore_configuration':'Pore functionalization/passivation to which a result applies.',
 'CH4_barrier':'Energy barrier specifically for CH4.',
 'H2_barrier':'Energy barrier specifically for H2.',
 'fabrication_techniques':'Explicit fabrication alternatives; no Cartesian assignment of results.',
 'direction':'Direction of change of the target parameter or parameter state: increase, decrease, unchanged, unspecified.',
 'contribution':'Explicit partial, dominant or joint explanatory contribution; no numeric fraction inferred.',
 'scope':'Whether the claim is collective or independently distributive.',
 'joint_requirement':'Conjunction semantics for a requirement bundle: all must hold simultaneously.',
 'evidence_basis':'Whether support is calculation, experiment or review; separate from modality.',
 'strength':'Literal qualitative strength, such as strongly or significantly.',
 'target_parameter':'Names the parameter state when wording is a magnitude of decrease rather than the underlying current.',
 'width':'Literal pore width, retaining the source unit A without silently substituting angstrom.',
 'explanatory_basis':'Joint explanatory features retained as one source-grounded qualifier.',
 'outcome_scope':'Named behavior explained by a mechanism or explanatory claim.',
}

CONTROLLED = {
 'direction':['increase','decrease','unchanged','unspecified'],
 'contribution':['partial','dominant','joint'],
 'scope':['collective','individual'],
 'joint_requirement':['all'],
 'evidence_basis':['calculation','experiment','review'],
}

def build_spec(drafts, decisions, input_manifest):
    observed = defaultdict(set)
    values = defaultdict(list)
    examples = {}
    for d in drafts:
        mm = {m['mention_id']:m for m in d['mentions']}
        for a in d['assertions']:
            examples.setdefault(a['relation_type'], {
                'document_code':d['document_code'], 'assertion_id':a['assertion_id'],
                'head':mm[a['head_mention_id']]['surface_text'], 'tail':mm[a['tail_mention_id']]['surface_text'],
                'polarity':a['polarity'],'modality':a['modality'], 'evidence':a['evidence'],
                'qualifiers':a['qualifiers'],
            })
            for q in a['qualifiers']:
                observed[a['relation_type']].add(q['qualifier_type'])
                values[q['qualifier_type']].append(q)
    relations = {}
    for name, (definition,direction,heads,tails,contrast,difference) in RELATIONS.items():
        allowed = observed[name] | {'analyte_scope','material_configuration','evidence_basis','scope_limit','scope'}
        if name in ['CAUSES','EXPLAINS','CHANGES_PARAMETER','DEPENDS_ON']:
            allowed |= {'strength','contribution','direction','target_parameter','outcome_scope','comparison'}
        required = {'direction':{'enum':CONTROLLED['direction']}} if name == 'CHANGES_PARAMETER' else {}
        if name == 'MEETS_REQUIREMENT':
            required = {'joint_requirement':{'enum':['all']},'scope':{'enum':['collective']}}
            allowed |= set(required)
        relations[name] = {
            'definition':definition,'direction':direction,'head_kinds':heads,'tail_kinds':tails,
            'required_qualifiers':required,'optional_qualifiers':sorted(allowed-set(required)),
            'supported_polarities':['POSITIVE','NEGATIVE'],
            'supported_modalities':['ASSERTED','PROPOSED','COMPARED','HYPOTHETICAL'],
            'positive_example':examples[name], 'contrast':contrast,'nearest_relations':difference,
            'ambiguity_policy':'Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.',
            'group_policy':'Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.',
        }
    relations['HAS_MEMBER']['endpoint_pairs'] = [[x,x] for x in ['PROPERTY','PROCESS','MATERIAL','ANALYTE','MORPHOLOGY','MECHANISM']] + [['PROPERTY','PERFORMANCE']]
    relations['HAS_MEMBER']['head_contextual_roles'] = ['explicit_group','requirement_bundle']
    relations['HAS_MEMBER']['mixed_kind_rule'] = 'PROPERTY -> PERFORMANCE only for a requirement_bundle head.'
    relations['MEETS_REQUIREMENT']['tail_contextual_roles'] = ['requirement_bundle']
    qualifiers = {}
    for key, definition in QUALIFIER_DEFINITIONS.items():
        vv = values[key]
        types = sorted({('number' if isinstance(q['raw_value'],(int,float)) and not isinstance(q['raw_value'],bool) else 'array' if isinstance(q['raw_value'],list) else 'string') for q in vv}) or ['string']
        qualifiers[key] = {'definition':definition,'raw_value_types':types,
            'unit_policy':'Preserve the exact source unit; no implicit normalization.',
            'attachment':'applies_to_assertion_id must equal containing assertion; evidence_refs must be registered exact subspans covered by its evidence.',
            'normalization':'normalized_value may remain null; controlled semantic values in raw_value are AI interpretations grounded in raw_text.',
        }
        if key in CONTROLLED: qualifiers[key]['enum'] = CONTROLLED[key]
    return {
        'ontology_id':ONTOLOGY_ID,'version':'1.0','status':'TECHNICALLY_FROZEN_PENDING_HUMAN_APPROVAL',
        'technical_freeze':{'identity_file':'FREEZE_MANIFEST.json','content_final':True,'hashes_created_by':'repository integration'},
        'approval':{'final_human_ontology_approved':False,'annotation_human_review_status':'NOT_REVIEWED','human_gold_documents':0,
            'ai_adjudication_actor':'AI','user_decision_scope':'Earlier individual Q1-Q6 constraints, where recorded, are design instructions; they do not approve labels or the final ontology.',
            'technical_freeze_is_human_approval':False},
        'entities':{k:{'definition':v[0],'examples':v[1],'boundary':v[2],'canonicalization':v[3]} for k,v in ENTITIES.items()},
        'relations':relations,'qualifiers':qualifiers,
        'qualifier_schema':{'required_fields':['qualifier_type','raw_text','raw_value','unit','applies_to_assertion_id','evidence_refs'],
            'optional_fields':['normalized_value','comparator','status'],'unknown_types':'reject in accepted assertions; record unresolved candidates',
            'required_qualifier_rule_format':'Mapping qualifier_type -> constraints, including enum on raw_value.'},
        'polarity':{'POSITIVE':'The relation is affirmed.','NEGATIVE':'The relation is explicitly negated; negation scope remains local.','UNKNOWN':'Uncertain polarity; candidate/abstention only, not SUPPORTED.'},
        'modality':{'ASSERTED':'Author presents the statement as holding, including calculated results.','PROPOSED':'Author proposes or suggests a mechanism, explanation or design.','COMPARED':'A comparative assertion with its source-stated comparator.','HYPOTHETICAL':'Possibility, potential, goal or future capability, without demonstrated realization.','UNKNOWN':'Unresolved author stance; candidate/abstention only.'},
        'support_policy':{'accepted':'SUPPORTED + DIRECT_SOURCE + AI_DRAFT; this means source support, not independently established physical truth.','abstention':'INSUFFICIENT_EVIDENCE decisions retain UNRESOLVED candidates and evidence; REJECT candidates remain in immutable decision records.'},
        'evidence_policy':{'offsets':'Python Unicode codepoints [start,end), relative to frozen chunk text.','required':'At least one exact source evidence span for each accepted assertion; source text and SHA-256 must match.','qualifier_grounding':'Exact raw_text span and matching assertion attachment required.','source_context':'Record source_relation_type, source_modality, source_polarity, interpretation_basis=AI_DEV_SOURCE_REVIEW, and evidence_span_ids as an AI regression interpretation; not an independent semantic oracle.','no_transitive_facts':True,'absence_is_not_negation':True},
        'canonicalization':{'normalization_version':ONTOLOGY_ID,'identity_levels':['concept','source-scoped configuration','experimental instance'],
            'cannot_merge':['graphene / graphene oxide','graphene oxide / reduced graphene oxide','different compositions or dopants','different device configurations absent explicit identity'],
            'same_policy':'Only aliases or co-reference established by this source license SAME. RELATED/BROADER/NARROWER are not identity. Chemical class membership is not SAME.',
            'unicode':'Preserve source Unicode; chemical spacing normalization is conceptual only; original spans stay unchanged.'},
        'group_policy':{'explicit_group_required':True,'membership_does_not_distribute':True,'cartesian_products_forbidden':True,'joint_negation':'NEGATIVE MEETS_REQUIREMENT with joint_requirement=all means NOT(all); no member-specific negation follows.','mixed_requirements':'PROPERTY requirement_bundle can contain PROPERTY/PERFORMANCE members; no new entity kind needed.'},
        'provenance':{'design_split':'DEV','design_document_count':12,'question_count':20,'candidate_count':26,'inputs_manifest':'INPUT_MANIFEST.json','snapshot_directory':'source_snapshot','isolation':'Semantic design used a fresh isolated agent context and only the enumerated DEV bundle. Parent session had earlier evaluation exposure; end-to-end historical independence cannot be proved.','historical_limitation':'The first 0.3 freeze persistence failed, evaluation text was shown before retry. Historical artifacts are preserved and not retroactively claimed perfectly isolated.','ai_self_audit':'Two separate logical passes by the same AI; not independent human review.'},
        'proposal_disposition':{'INCREASES':'MAP_TO_EXISTING: CHANGES_PARAMETER + direction=increase; physical increase kept distinct from IMPROVES.','DECREASES':'Covered by CHANGES_PARAMETER + direction=decrease, grounded in D078.','DOMINATES':'MAP_TO_EXISTING: EXPLAINS + contribution=dominant + collective scope.','USED_FOR_DEVICE_RANGE':'Not admitted: DEV impact wording is insufficient to establish device-directed use; D024-Q6/Q7 remain unresolved.'},
    }
