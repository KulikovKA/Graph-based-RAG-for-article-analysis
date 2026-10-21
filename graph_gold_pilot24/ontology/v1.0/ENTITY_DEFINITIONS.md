# Entity definitions and identity

The 12 existing kinds are retained. Mentions have a contextual role and exact Unicode spans. A source may refer to a chemical as a dopant in one clause and as an analyte in another; the role does not change chemical identity. Groups use an existing semantic kind and an explicit group role. A mixed requirement bundle uses PROPERTY with contextual_role=requirement_bundle.

## MATERIAL

A substance, composition, or material system considered as matter.

Examples: graphene; graphene oxide; reduced graphene oxide; Ti3C2Tx MXene.

Boundary: A fabricated sensor or functional component is DEVICE; a material may FUNCTIONS_AS a device component without becoming identical to it.

Canonicalization: Preserve composition, oxidation, dopant and defect distinctions; expand locally defined aliases only.

## DEVICE

An engineered object or functional physical component with a technical role.

Examples: gas sensor; electrode; sensing layer; membrane.

Boundary: A pore, junction or electronic layer described as structure is MORPHOLOGY; a manufactured electrode layer is DEVICE.

Canonicalization: Separate device class from source-scoped configuration and experimental instance.

## PROPERTY

A physical, chemical, structural or manufacturing attribute or parameter of a bearer.

Examples: hole concentration; oxygen atomic ratio; adsorption energy; noise; pore width.

Boundary: Sensitivity, selectivity, detection limit and task response are PERFORMANCE; a geometric structure is MORPHOLOGY.

Canonicalization: Keep parameter identity distinct from value, direction of change, condition and bearer instance.

## PERFORMANCE

A capability, task outcome or evaluation measure in an application.

Examples: sensitivity; selectivity; response; detection limit; sensing stability.

Boundary: Physical conductivity, carrier concentration and noise are PROPERTY even when they explain performance.

Canonicalization: Do not identify measurements across different analytes, configurations or conditions; retain those attachments.

## ANALYTE

A substance or explicit substance class in the contextual role of target, adsorbate or comparison gas.

Examples: NH3 target; NO2 target; comparison gases/VOCs.

Boundary: NO2 used as dopant in D060 is MATERIAL; do not turn a generic gas mention into a specific chemical.

Canonicalization: Role-specific mention kind does not assert a different chemical species; no SAME link between different compounds.

## PROCESS

A technical action, transformation, operation or event, including formation and measurement.

Examples: microwave treatment; adsorption; junction formation; n-doping.

Boundary: MECHANISM describes how or why a phenomenon occurs; the event it involves remains PROCESS.

Canonicalization: Keep the event of formation distinct from the resulting object and from a named method family.

## MECHANISM

A source-expressed explanation, interaction, or combined explanatory account of technical behavior.

Examples: electrostatic interaction; sensing mechanism; combined current and mobility effects.

Boundary: A junction itself is MORPHOLOGY; formation is PROCESS; do not promote every process into an explanation.

Canonicalization: Preserve the scope of hypothesized accounts and joint explanations; no inferred quantitative cancellation.

## OPERATING_CONDITION

An environmental, sample or operating circumstance under which a claim applies.

Examples: 150 °C; room temperature; gas mixture with reducing gases.

Boundary: A measured outcome is PROPERTY/PERFORMANCE. A laser setting can be PROPERTY of a process.

Canonicalization: Normalize only explicit, unambiguous units and retain original values; room temperature is not silently 25 °C.

## MORPHOLOGY

A structural arrangement, shape, geometry or electronic/spatial feature.

Examples: heterojunction; pore; electron accumulation/depletion layer; charged impurities.

Boundary: Material composition is MATERIAL; engineered sensing/electrode components are DEVICE; carrier concentration is PROPERTY.

Canonicalization: Preserve junction composition, pore passivation, electronic layer type and location; never equate interfaces with their formation.

## TECHNOLOGY

A named technology or method family referenced as an approach.

Examples: density functional theory; electron-beam technology.

Boundary: A concrete execution or transformation is PROCESS; a technical end use is APPLICATION.

Canonicalization: A source may name a method family and an execution separately; RELATED does not imply SAME.

## APPLICATION

An explicitly named end use, task or application field.

Examples: gas separation; breath analysis; gas sensing; disease diagnostics.

Boundary: A device class such as fuel cell remains DEVICE; vague impact on it does not by itself establish USED_FOR.

Canonicalization: Preserve application scope and prospective modality; do not turn discussion of a field into a fabricated device.

## OTHER

A source-expressed technical referent that does not fit the other kinds.

Examples: clothes as receiving host; functional template role.

Boundary: Use only after checking the specific kinds; contextual_role can mark a role or group without adding a new kind.

Canonicalization: Keep source-scoped identity; OTHER is not permission to relax relation domains.

## Context, identity and source scope

D010 electron accumulation and depletion layers and p–n junctions are MORPHOLOGY; the manufactured sensing/electrode layer in D003 is DEVICE. D004 formation is PROCESS, while the junctions it produces are MORPHOLOGY. D078 charged impurities are electronic structure, not a new material formulation by inference.

Use SAME only for source-supported aliases or co-reference. Related class membership, chemical similarity, shared role, and a material serving as a device component never establish SAME. Keep graphene ≠ GO ≠ rGO and separate dopants, stoichiometries, pore passivations, and device configurations. A concept identifier is not proof that two measurements came from the same experimental instance. Preserve original cannot-link decisions. New mentions retain revision-local instance scope and deterministic identifiers.

A coordinated list is not automatically an entity identity. HAS_MEMBER expresses explicit enumeration. PROPERTY→PERFORMANCE membership is allowed only for a requirement bundle; other admitted member pairs share kind. No group assertion distributes without independent source support.
