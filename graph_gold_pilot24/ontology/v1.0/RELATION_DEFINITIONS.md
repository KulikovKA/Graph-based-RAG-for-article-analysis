# Ontology v1.0 relation definitions

Status: TECHNICALLY_FROZEN_PENDING_HUMAN_APPROVAL. Semantic design input: the isolated 12-document DEV bundle. All examples below are exact frozen source evidence. Positive annotation examples may contain explicit negative source claims; polarity is shown.

Each predicate is directed. The machine constraints, controlled qualifier values, endpoint pairs and examples are authoritative in `ontology.json`. Unknown author stance or polarity remains a candidate, never a supported assertion. All groups obey the shared no-distribution/no-Cartesian-product policy.

## HAS_PROPERTY

The bearer has the stated non-task physical, chemical, structural or process attribute.

Direction: `bearer -> property`. Domain: DEVICE, MATERIAL, PROCESS, OTHER, MORPHOLOGY. Range: PROPERTY.

Required qualifiers: none.
Optional qualifiers: CH4_barrier, H2_barrier, analyte_scope, associated_change, change, comparison, evidence_basis, mass_ratio, material_configuration, optimization_status, pore_configuration, relative_humidity, scope, scope_limit, trend, width.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D001**, `f50ea985-9822-55e7-8fe1-c81b67a01955`: E-textiles → low cost (POSITIVE, ASSERTED).

Evidence: chunk `6319af2d-0fe1-4daa-87c6-131c379a75c9`, Unicode [0,168), SHA-256 `51d6b3595cc1b465fba348487a2c2784ee54f3ce01e850c9bea6eb5d424b0831`.

> E-textiles are gaining growing popularity recently due to low cost, light weight, and conformable compatibility with clothes in wearable and portable smart electronics.

Contrast: Hole concentration belongs here; sensitivity belongs under HAS_PERFORMANCE. An increase in concentration also needs CHANGES_PARAMETER.

Difference: HAS_PERFORMANCE measures task outcomes; DEPENDS_ON relates a dependent quantity to its explanatory variable.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## HAS_PERFORMANCE

The bearer exhibits the stated task capability, measured outcome or performance limitation.

Direction: `bearer -> performance`. Domain: DEVICE, MATERIAL. Range: PERFORMANCE.

Required qualifiers: none.
Optional qualifiers: NO2_detection_limit, NO2_response_per_concentration, NO_detection_limit, NO_response_per_concentration, SNR_ratio, analyte_concentration, analyte_scope, bending_cycles, coefficient_of_determination, comparison, comparison_direction, comparison_material, detection_limit, detection_limit_range, doped_detection_limit, duration, estimation_status, evidence_basis, gas_pair, material_configuration, pore_configuration, relative_humidity_range, relative_sensitivity, response, scope, scope_limit, selectivity_comparison, selectivity_order, strain, stretch, temperature, temperature_selection, twisting_cycles, undoped_detection_limit.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D001**, `8e57c346-291c-5859-804e-9e7a7a3fa816`: as-prepared fiber → sensitive sensing response (POSITIVE, ASSERTED).

Evidence: chunk `6319af2d-0fe1-4daa-87c6-131c379a75c9`, Unicode [609,928), SHA-256 `51d6b3595cc1b465fba348487a2c2784ee54f3ce01e850c9bea6eb5d424b0831`.

> The as-prepared fiber demonstrates sensitive sensing response, excellent long-term stability (84 days), low theoretical detection limit (43.5 ppb NO 2 ), great mechanical deformation tolerance (3000 bending cycles, 1000 twisting cycles and 65% strain strength), and washing durability in room-temperature gas detection.

Contrast: D060 hole concentration is a physical parameter, not performance. D078 nonresponse is a negative response claim, not absence of a physical component.

Difference: HAS_PROPERTY describes intrinsic/operational attributes; performance comparisons keep their comparator and modality.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## HAS_MORPHOLOGY

The bearer has a stated structural, geometric or electronic arrangement.

Direction: `bearer -> structure`. Domain: DEVICE, MATERIAL. Range: MORPHOLOGY.

Required qualifiers: none.
Optional qualifiers: analyte_scope, evidence_basis, material_configuration, scope, scope_limit.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D001**, `8a663f4c-0033-5681-8006-4e061a927f7d`: mesoporous zinc oxide nanosheets → mesoporous (POSITIVE, ASSERTED).

Evidence: chunk `6319af2d-0fe1-4daa-87c6-131c379a75c9`, Unicode [385,608), SHA-256 `51d6b3595cc1b465fba348487a2c2784ee54f3ce01e850c9bea6eb5d424b0831`.

> The proposed gas sensor is built using commercially available cotton/elastic threads as flexible/stretchable templates and reduced graphene oxide/mesoporous zinc oxide nanosheets as sensing layers to form conducting fibers.

Contrast: A junction is a structure; its formation is an event. Physical material constituents use HAS_COMPONENT.

Difference: HAS_COMPONENT is physical composition; MORPHOLOGY includes electronic interfaces and spatial organization.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## HAS_COMPONENT

The composite or device explicitly contains the physical material or functional component.

Direction: `whole -> physical component`. Domain: DEVICE, MATERIAL. Range: DEVICE, MATERIAL.

Required qualifiers: none.
Optional qualifiers: analyte_scope, evidence_basis, layer_position, location, material_configuration, scope, scope_limit.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D001**, `98421599-20f7-50ca-926f-0c6075107254`: reduced graphene oxide/mesoporous zinc oxide nanosheets → reduced graphene oxide (POSITIVE, ASSERTED).

Evidence: chunk `6319af2d-0fe1-4daa-87c6-131c379a75c9`, Unicode [385,608), SHA-256 `51d6b3595cc1b465fba348487a2c2784ee54f3ce01e850c9bea6eb5d424b0831`.

> The proposed gas sensor is built using commercially available cotton/elastic threads as flexible/stretchable templates and reduced graphene oxide/mesoporous zinc oxide nanosheets as sensing layers to form conducting fibers.

Contrast: A list of seven candidate nanocomposites is a group with HAS_MEMBER, not seven physical parts of one nanocomposite.

Difference: HAS_MEMBER is enumerated membership; USES_MATERIAL records the device/material role without requiring part identity.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## HAS_MEMBER

An explicitly expressed collection has the listed member; this does not distribute the collection claim to its members.

Direction: `explicit group -> member`. Domain: PROPERTY, PROCESS, MATERIAL, ANALYTE, MORPHOLOGY, MECHANISM. Range: PROPERTY, PERFORMANCE, PROCESS, MATERIAL, ANALYTE, MORPHOLOGY, MECHANISM.

Required qualifiers: none.
Optional qualifiers: analyte_scope, evidence_basis, material_configuration, scope, scope_limit.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D001**, `cd7b7344-98d3-5924-877e-e75d8d9e3053`: repairability, reliability, stability, and practicability → repairability (POSITIVE, ASSERTED).

Evidence: chunk `e9796bf6-68c8-440f-a814-ca185157cce3`, Unicode [0,320), SHA-256 `272bcd1547345d4fa14705d9e0af1c56a2d5692244e2bb2b8f3b8b04b12da3a3`.

> More significantly, scalable wearable characteristics including repairability, reliability, stability, and practicability have been efficiently improved, which are achieved by knotting the fractured fibers, incorporating multiple sensors in series/parallel and weaving multisensor array networks integrated into clothes.

Contrast: D026 failure to meet all requirements cannot be converted to failure of each requirement. A composite is not a list of alternatives.

Difference: HAS_COMPONENT is physical parthood. Membership never licenses a Cartesian product of relations between two lists.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## USES_MATERIAL

A device explicitly employs a material in its construction or functioning.

Direction: `device -> material`. Domain: DEVICE. Range: MATERIAL.

Required qualifiers: none.
Optional qualifiers: analyte_scope, evidence_basis, material_configuration, scope, scope_limit.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D001**, `0f2427bf-8600-58a4-8a0e-c16f7bba1b25`: gas sensor → cotton/elastic threads (POSITIVE, ASSERTED).

Evidence: chunk `6319af2d-0fe1-4daa-87c6-131c379a75c9`, Unicode [385,608), SHA-256 `51d6b3595cc1b465fba348487a2c2784ee54f3ce01e850c9bea6eb5d424b0831`.

> The proposed gas sensor is built using commercially available cotton/elastic threads as flexible/stretchable templates and reduced graphene oxide/mesoporous zinc oxide nanosheets as sensing layers to form conducting fibers.

Contrast: NO2 used to dope a sensor is not automatically an analyte detected by it.

Difference: FUNCTIONS_AS links material to a functional component role; HAS_COMPONENT records explicit physical composition.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## FUNCTIONS_AS

A material explicitly serves as the named functional component or role.

Direction: `material -> functional component/role`. Domain: MATERIAL. Range: DEVICE, OTHER.

Required qualifiers: none.
Optional qualifiers: analyte_scope, evidence_basis, material_configuration, scope, scope_limit.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D001**, `c98893f2-5b7e-5193-b822-9924c7effa53`: cotton/elastic threads → flexible/stretchable templates (POSITIVE, ASSERTED).

Evidence: chunk `6319af2d-0fe1-4daa-87c6-131c379a75c9`, Unicode [385,608), SHA-256 `51d6b3595cc1b465fba348487a2c2784ee54f3ce01e850c9bea6eb5d424b0831`.

> The proposed gas sensor is built using commercially available cotton/elastic threads as flexible/stretchable templates and reduced graphene oxide/mesoporous zinc oxide nanosheets as sensing layers to form conducting fibers.

Contrast: Porous graphene functioning as a membrane does not make the material concept identical to every membrane.

Difference: USED_FOR links to an end use; FUNCTIONS_AS names what the material serves as.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## DETECTS

The sensor has an explicitly stated detection capability for the target substance, including explicit nonresponse and prospective capability.

Direction: `sensor -> target analyte`. Domain: DEVICE. Range: ANALYTE.

Required qualifiers: none.
Optional qualifiers: analyte_concentration, analyte_scope, concentration_regime, evidence_basis, material_configuration, response_per_concentration, scope, scope_limit, temperature.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D001**, `6c739cd3-4e69-547f-8bfe-ffc34ed99d07`: as-prepared fiber → NO 2 (POSITIVE, ASSERTED).

Evidence: chunk `6319af2d-0fe1-4daa-87c6-131c379a75c9`, Unicode [609,928), SHA-256 `51d6b3595cc1b465fba348487a2c2784ee54f3ce01e850c9bea6eb5d424b0831`.

> The as-prepared fiber demonstrates sensitive sensing response, excellent long-term stability (84 days), low theoretical detection limit (43.5 ppb NO 2 ), great mechanical deformation tolerance (3000 bending cycles, 1000 twisting cycles and 65% strain strength), and washing durability in room-temperature gas detection.

Contrast: Selectivity over SO2 does not establish detection of SO2; a dopant is not automatically a detected gas.

Difference: USED_FOR describes an end use; DETECTS requires a target and a detection claim.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## USED_FOR

The object has an explicitly stated actual, proposed or hypothetical application, process use or material sensing target.

Direction: `object -> stated use`. Domain: DEVICE, MATERIAL. Range: APPLICATION, PROCESS, ANALYTE.

Required qualifiers: none.
Optional qualifiers: analyte_scope, concentration_regime, evidence_basis, material_configuration, monitoring_times, sample_condition, scope, scope_limit, temperature.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D001**, `2461a1dd-08a1-55c0-9478-5fd7c0a1df0a`: E-textiles → wearable and portable smart electronics (POSITIVE, ASSERTED).

Evidence: chunk `6319af2d-0fe1-4daa-87c6-131c379a75c9`, Unicode [0,168), SHA-256 `51d6b3595cc1b465fba348487a2c2784ee54f3ce01e850c9bea6eb5d424b0831`.

> E-textiles are gaining growing popularity recently due to low cost, light weight, and conformable compatibility with clothes in wearable and portable smart electronics.

Contrast: D024 a pore could have impact on fuel cells does not establish porous graphene USED_FOR a fabricated fuel cell.

Difference: FUNCTIONS_AS names the component role; DETECTS is sensor capability; topic mention and vague impact are insufficient.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## FABRICATED_BY

The object is obtained by the stated fabrication process, within the source modality.

Direction: `fabricated object -> fabrication process`. Domain: DEVICE, MATERIAL. Range: PROCESS.

Required qualifiers: none.
Optional qualifiers: analyte_scope, equipment, evidence_basis, material_configuration, parameter_selection, scope, scope_limit.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D001**, `98de89d5-d9f3-5ff2-9808-cb326e4cab9f`: fiber gas sensor → fabricating strategy (POSITIVE, ASSERTED).

Evidence: chunk `6319af2d-0fe1-4daa-87c6-131c379a75c9`, Unicode [169,384), SHA-256 `51d6b3595cc1b465fba348487a2c2784ee54f3ce01e850c9bea6eb5d424b0831`.

> Here, an easy-handing, low cost, and scalable fabricating strategy is reported to fabricate conductive, highly flexible, and mechanically stretchable/twisted fiber gas sensor with great wearability and knittability.

Contrast: A characterization process acting on a product is not its fabrication method.

Difference: ACTS_ON relates process to object; FABRICATED_BY asserts production of that object.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## IMPROVES

The process is stated to make a property or task outcome better in the source-defined evaluative sense.

Direction: `process -> improved property/performance`. Domain: PROCESS. Range: PROPERTY, PERFORMANCE.

Required qualifiers: none.
Optional qualifiers: analyte_scope, epistemic_basis, evidence_basis, improvement_factor, material_configuration, scope, scope_limit.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D001**, `dbc6e834-cfce-5e44-97eb-ca7af1388265`: knotting the fractured fibers, incorporating multiple sensors in series/parallel and weaving multisensor array networks integrated into clothes → repairability, reliability, stability, and practicability (POSITIVE, ASSERTED).

Evidence: chunk `e9796bf6-68c8-440f-a814-ca185157cce3`, Unicode [0,320), SHA-256 `272bcd1547345d4fa14705d9e0af1c56a2d5692244e2bb2b8f3b8b04b12da3a3`.

> More significantly, scalable wearable characteristics including repairability, reliability, stability, and practicability have been efficiently improved, which are achieved by knotting the fractured fibers, incorporating multiple sensors in series/parallel and weaving multisensor array networks integrated into clothes.

Contrast: Increasing hole concentration is a direction of physical change, not inherently an improvement; decreasing detection limit can be an improvement.

Difference: CHANGES_PARAMETER has a signed or unspecified physical change; OPTIMIZES is adjustment of an object/configuration.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## ACTS_ON

The process explicitly acts on, characterizes, transforms or otherwise operates on the object.

Direction: `process -> affected/studied object`. Domain: PROCESS. Range: DEVICE, MATERIAL.

Required qualifiers: none.
Optional qualifiers: analyte_scope, dopant, evidence_basis, fabrication_techniques, material_configuration, scope, scope_limit, support_method.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D001**, `7065f46d-83cf-5816-90ff-f106128ba135`: knotting the fractured fibers → fractured fibers (POSITIVE, ASSERTED).

Evidence: chunk `e9796bf6-68c8-440f-a814-ca185157cce3`, Unicode [0,320), SHA-256 `272bcd1547345d4fa14705d9e0af1c56a2d5692244e2bb2b8f3b8b04b12da3a3`.

> More significantly, scalable wearable characteristics including repairability, reliability, stability, and practicability have been efficiently improved, which are achieved by knotting the fractured fibers, incorporating multiple sensors in series/parallel and weaving multisensor array networks integrated into clothes.

Contrast: DFT study of a group of surfaces and gases does not justify sixteen separate sensing-use claims.

Difference: FABRICATED_BY asserts object production; ACTS_ON does not imply an improved or fabricated outcome.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## INTEGRATED_IN

The functional object is explicitly incorporated into the receiving host.

Direction: `integrated object -> host`. Domain: DEVICE. Range: DEVICE, OTHER.

Required qualifiers: none.
Optional qualifiers: analyte_scope, evidence_basis, material_configuration, scope, scope_limit.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D001**, `2455c001-da04-5095-bd51-df7e6bd35ab7`: multisensor array networks → clothes (POSITIVE, ASSERTED).

Evidence: chunk `e9796bf6-68c8-440f-a814-ca185157cce3`, Unicode [0,320), SHA-256 `272bcd1547345d4fa14705d9e0af1c56a2d5692244e2bb2b8f3b8b04b12da3a3`.

> More significantly, scalable wearable characteristics including repairability, reliability, stability, and practicability have been efficiently improved, which are achieved by knotting the fractured fibers, incorporating multiple sensors in series/parallel and weaving multisensor array networks integrated into clothes.

Contrast: A material merely proposed for an application is not already integrated into that device.

Difference: HAS_COMPONENT gives whole-to-part direction; INTEGRATED_IN gives inserted-object-to-host direction.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## HAS_MECHANISM

The device or material has the stated source-expressed mechanism for its specified behavior.

Direction: `device/material bearer -> mechanism`. Domain: DEVICE, MATERIAL. Range: MECHANISM.

Required qualifiers: none.
Optional qualifiers: analyte_scope, contribution, evidence_basis, explained_capability, material_configuration, outcome_scope, scope, scope_limit.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D003**, `d65ad610-3c52-5bf0-b838-9979bbde1caf`: gas sensor → design of a stretchable serpentine structure in the LIG electrode and strain isolation from the stiff island (POSITIVE, ASSERTED).

Evidence: chunk `0ad16539-951a-4c6a-95df-0d92179b23eb`, Unicode [859,1017), SHA-256 `93b3b8cd46f210f24559ada46e4094b348260a9b1c0be1b96965d77ac32e55ae`.

> The design of a stretchable serpentine structure in the LIG electrode and strain isolation from the stiff island allows the gas sensor to be stretched by 30%.

Contrast: The mechanism explains behavior; it is not a material constituent. An absent interaction with NH3 must keep NEGATIVE polarity and its target scope.

Difference: EXPLAINS links explanatory factor to an outcome, while HAS_MECHANISM links bearer to its explanatory account.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## MECHANISM_INVOLVES

The mechanism explicitly involves the named subordinate mechanism, process or structure.

Direction: `mechanism -> involved mechanism/event/structure`. Domain: MECHANISM. Range: MECHANISM, PROCESS, MORPHOLOGY.

Required qualifiers: none.
Optional qualifiers: analyte_scope, evidence_basis, isolation_reference, material_configuration, scope, scope_limit.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D003**, `3fcfd6a9-2d61-5932-a80e-61ba8d224f3e`: design of a stretchable serpentine structure in the LIG electrode and strain isolation from the stiff island → design of a stretchable serpentine structure (POSITIVE, ASSERTED).

Evidence: chunk `0ad16539-951a-4c6a-95df-0d92179b23eb`, Unicode [859,1017), SHA-256 `93b3b8cd46f210f24559ada46e4094b348260a9b1c0be1b96965d77ac32e55ae`.

> The design of a stretchable serpentine structure in the LIG electrode and strain isolation from the stiff island allows the gas sensor to be stretched by 30%.

Contrast: Electron accumulation layer is a structure involved in the mechanism; the layer is not the complete sensing mechanism.

Difference: HAS_COMPONENT is physical parthood; CAUSES asserts production and is stronger than mere involvement.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## LOCATED_IN

The electronic or geometric structure is explicitly situated in the named material.

Direction: `structure -> containing material`. Domain: MORPHOLOGY. Range: MATERIAL.

Required qualifiers: none.
Optional qualifiers: analyte_scope, evidence_basis, material_configuration, scope, scope_limit.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D010**, `e6ea4dae-f0cc-5ddd-aafb-72b3281d8134`: electron accumulation layer → GO/CuO/ZnO (POSITIVE, PROPOSED).

Evidence: chunk `761f757f-5005-4417-bf90-f2c5200f7600`, Unicode [363,588), SHA-256 `c96d836b51f3c30b23d69406198bde211107fed455cd9631385c370269084ab3`.

> The NH 3 -sensing mechanism was proposed based on the modulation of complex p–n heterojunctions via the electron accumulation layer in the n-type of GO/CuO/ZnO and the electron depletion layer in the p-type Ti 3 C 2 Tx Mxene.

Contrast: The electron depletion layer in p-type Ti3C2Tx is not located in GO/CuO/ZnO; preserve the attachment in D010.

Difference: HAS_MORPHOLOGY is bearer-to-structure and does not by itself encode the stated specific location.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## OPTIMIZES

A process explicitly adjusts an object or configuration described as optimized or optimal for a stated technical objective.

Direction: `adjustment process -> optimized object`. Domain: PROCESS. Range: DEVICE, MATERIAL.

Required qualifiers: none.
Optional qualifiers: analyte_scope, evidence_basis, material_configuration, scope, scope_limit.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D003**, `30301f7a-cfcd-5947-9f02-63b749e88859`: tuning laser processing parameters → LIG sensing and electrode layer (POSITIVE, ASSERTED).

Evidence: chunk `0ad16539-951a-4c6a-95df-0d92179b23eb`, Unicode [331,575), SHA-256 `93b3b8cd46f210f24559ada46e4094b348260a9b1c0be1b96965d77ac32e55ae`.

> Sandwiched between a soft elastomeric substrate and a moisture-resistant semipermeable encapsulant, the LIG sensing and electrode layer is first optimized by tuning laser processing parameters such as power, image density, and defocus distance.

Contrast: D024 tuning selectivity and diffusivity does not establish an optimum; it uses CHANGES_PARAMETER with unspecified direction.

Difference: IMPROVES targets a better attribute; neutral tuning is CHANGES_PARAMETER, and optimization must be explicit.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## FACILITATES

A material or process promotes or enables the named process without asserting strict production of its outcome.

Direction: `facilitating material/process -> facilitated process`. Domain: MATERIAL, PROCESS. Range: PROCESS.

Required qualifiers: none.
Optional qualifiers: analyte_scope, evidence_basis, explanatory_basis, material_configuration, process_location, scope, scope_limit.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D004**, `3d2e0168-bacc-5412-b779-0e6763e81edf`: graphene → efficient transport of the microwave energy (POSITIVE, ASSERTED).

Evidence: chunk `1314b88d-a703-48b5-bb03-e426d5474034`, Unicode [444,647), SHA-256 `5ab47cc03efc60802c5c6bece098307c9084b5e327212580366207ab757116c9`.

> By the microwave treatment of graphene–SnO 2 nanocomposites, with the graphene promoting efficient transport of the microwave energy, evaporation and redeposition of SnO x nanoparticles were facilitated.

Contrast: D004 graphene promotes microwave-energy transport, while microwave treatment facilitates evaporation/redeposition. Do not infer a direct graphene-to-evaporation edge.

Difference: CAUSES asserts that an event produces another event; EXPLAINS attributes behavior to a factor.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## CAUSES

A source explicitly states that the causal factor produces or induces the named technical event; event endpoints remain events.

Direction: `causal factor -> produced event`. Domain: PROCESS, MECHANISM, MATERIAL. Range: PROCESS.

Required qualifiers: none.
Optional qualifiers: analyte_scope, comparison, contribution, direction, evidence_basis, material_configuration, outcome_scope, scope, scope_limit, strength, target_parameter.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D004**, `fda0b6f7-50d4-5329-9479-9586a95ec805`: generation of SnO x nanoparticles and the SnO x phase in the matrix → formation of SnO 2 /SnO 2 homojunctions, SnO 2 /SnO x ( x < 2) heterojunctions, and SnO 2 /graphene heterojunctions (POSITIVE, PROPOSED).

Evidence: chunk `eb47e91a-4c35-4de7-96a3-f141eea0a6cf`, Unicode [0,321), SHA-256 `4fb5907a3a82cde6bcf412375e3883c2c52a669235fec58ce11b70619222a212`.

> We suggest that the generation of SnO x nanoparticles and the SnO x phase in the matrix results in the formation of SnO 2 /SnO 2 homojunctions, SnO 2 /SnO x ( x < 2) heterojunctions, and SnO 2 /graphene heterojunctions, which are responsible for the excellent sensitivity of the graphene–SnO 2 nanocomposites to NO 2 gas.

Contrast: D004 results in formation licenses CAUSES with PROPOSED modality. Merely promoting transport uses FACILITATES. A junction object cannot replace its formation event.

Difference: EXPLAINS attributes an outcome to a factor; signed parameter effects use CHANGES_PARAMETER when no separate produced event is needed.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## EXPLAINS

The source attributes an observed or proposed technical outcome or process to the explanatory factor, with the stated contribution and scope.

Direction: `explanatory factor -> explained outcome/process`. Domain: PROCESS, MECHANISM, MORPHOLOGY, PROPERTY. Range: PERFORMANCE, PROPERTY, PROCESS.

Required qualifiers: none.
Optional qualifiers: analyte_scope, comparison, contribution, direction, evidence_basis, material_configuration, outcome_scope, pore_configuration, scope, scope_limit, strength, target_parameter.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D003**, `13a447d3-bbb4-5e3d-bb07-9ec86cce8421`: design of a stretchable serpentine structure in the LIG electrode and strain isolation from the stiff island → stretched by 30% (POSITIVE, ASSERTED).

Evidence: chunk `0ad16539-951a-4c6a-95df-0d92179b23eb`, Unicode [859,1017), SHA-256 `93b3b8cd46f210f24559ada46e4094b348260a9b1c0be1b96965d77ac32e55ae`.

> The design of a stretchable serpentine structure in the LIG electrode and strain isolation from the stiff island allows the gas sensor to be stretched by 30%.

Contrast: A device possessing a mechanism is HAS_MECHANISM. Three junctions jointly responsible for sensitivity do not license independent, sufficient explanations by each junction.

Difference: CAUSES is event production; FACILITATES is enabling; EXPLAINS preserves attribution, partial contribution and dominant background explanation.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## CHANGES_PARAMETER

A factor changes or explicitly leaves unchanged the target physical/property or performance parameter; direction describes that parameter, not desirability.

Direction: `changing factor -> affected parameter`. Domain: PROCESS, MORPHOLOGY, MECHANISM. Range: PROPERTY, PERFORMANCE.

Required qualifiers: {"direction": {"enum": ["increase", "decrease", "unchanged", "unspecified"]}}.
Optional qualifiers: analyte_scope, comparison, contribution, evidence_basis, material_configuration, outcome_scope, scope, scope_limit, strength, target_parameter.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D060**, `3474a0cd-e488-53f9-9dd9-82ace9d3f4ec`: adsorption of NO2 molecules → hole concentration (POSITIVE, ASSERTED).

Evidence: chunk `006deffa-1906-4677-942b-2a29bd47046b`, Unicode [496,745), SHA-256 `7e3054e2cb1e788c55f6c5f17b4855b0993823ba82f68f8cf3c012bac4ed1393`.

> Electrical characterization and Raman spectroscopy measurements on graphene field-effect transistors show that adsorption of NO2 molecules significantly increases hole concentration in graphene, which results in the observed sensitivity enhancement.

Contrast: Increasing the magnitude of current decrease means direction=increase on the decrease magnitude; it must not become an increase in electric current.

Difference: IMPROVES is evaluative. Signed increases/decreases share one predicate; unspecified direction is valid only for an explicit change/tune statement.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## DEPENDS_ON

The source explicitly states that the head quantity/outcome depends on the tail parameter or structural configuration; no functional law is inferred.

Direction: `dependent quantity/outcome -> determining variable/configuration`. Domain: PROPERTY, PERFORMANCE. Range: PROPERTY, MORPHOLOGY.

Required qualifiers: none.
Optional qualifiers: analyte_scope, comparison, contribution, direction, evidence_basis, material_configuration, outcome_scope, scope, scope_limit, strength, target_parameter.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D078**, `943d8572-c7a6-5cd3-b884-76eb38015c23`: current decrease → number of amine functional groups (POSITIVE, ASSERTED).

Evidence: chunk `8e528f95-22fc-4b9a-8b16-90391b584bc3`, Unicode [233,429), SHA-256 `b0f5211d8a7b056bc9d7cccb1c371076afd5e4dc80f88e80baf6e7c51c26a088`.

> The exposure of the n-doped graphene to oxidizing gases such as NO 2 leads to a current decrease that depends strongly on the number of amine functional groups in various types of ethylene amines.

Contrast: Having a pore width is HAS_PROPERTY; depending on its width is DEPENDS_ON. Joint lists do not justify a four-edge Cartesian product.

Difference: HAS_PROPERTY is possession; EXPLAINS is attribution of an outcome; dependence does not establish the sign, causality or quantitative law.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.

## MEETS_REQUIREMENT

The material/device meets, or explicitly fails to meet, a jointly specified requirement bundle.

Direction: `evaluated bearer -> explicit joint requirement bundle`. Domain: MATERIAL, DEVICE. Range: PROPERTY.

Required qualifiers: {"joint_requirement": {"enum": ["all"]}, "scope": {"enum": ["collective"]}}.
Optional qualifiers: analyte_scope, evidence_basis, material_configuration, scope_limit.

Polarity: POSITIVE, NEGATIVE. Modality: ASSERTED, PROPOSED, COMPARED, HYPOTHETICAL.

DEV example: **D026**, `353bda66-bf30-57b4-8b2b-9cee1eff65a0`: existing sensor materials → two requirements (NEGATIVE, ASSERTED).

Evidence: chunk `5a1139f9-9bf1-4665-96e1-c15a6477ded6`, Unicode [263,438), SHA-256 `bedd2a7ed1ad17c747634824457042b37b609d742e51ee38b9ffc4f8c0f23907`.

> To obtain high sensitivity, two requirements need to be simultaneously satisfied: (i) low electrical noise and (ii) strong signal, which existing sensor materials cannot meet.

Contrast: Cannot simultaneously meet low noise AND strong signal means NOT(all requirements), not NOT(noise) AND NOT(signal).

Difference: HAS_PROPERTY/HAS_PERFORMANCE describe attributes individually; this relation preserves the conjunction and its negation.

Ambiguity: Abstain when the predicate, attachment, scope or endpoint referent is not licensed by the source. Preserve the weakest explicitly supported modality; no inferred transitive assertions.

Groups: Distribute only when grammar explicitly licenses each member claim. Otherwise use an exact-span group with HAS_MEMBER and scope=collective. Never infer Cartesian products.
