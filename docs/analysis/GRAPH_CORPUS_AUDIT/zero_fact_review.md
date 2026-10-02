# Manual review of all 11 zero-fact documents

Frozen source: `corpus_export.json`, exported 2026-10-02T12:34:50.953159+00:00; manifest SHA-256 `2842cf0909f29c7850a190a5418032548e67e0e220e4b15a539ca277ffb7b8bc`. No database or service calls were made in this audit.

## What the stored evidence establishes

All 11 records were read in normalized_json and in every associated stored chunk, together with source/document identity and extraction state. Every record is an indexed OpenAlex active revision with abstract status available, a nonempty abstract and a completed extraction marker with fact_count=0. The export also contains zero actual GraphFact rows for those same revisions.

Stored chunks exactly equal the corresponding normalized abstract spans, begin at position zero and reach the abstract end. All nonwhitespace abstract content is covered. D015 has three chunks separated only by single spaces; the other ten records have one chunk each. This rules out missing stored content and loss between the normalized abstract and stored chunks for these records. It does not establish that the OpenAlex abstract equals full article text or that no earlier upstream shortening occurred.

The source identity and abstract availability fields agree between the document and normalized payload. The shared extractor version is `graph-extraction-v2:qwen3.5:4b-q4_K_M@2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`; vocabulary is `technical-feature-v1`. Completion markers do not distinguish an empty model response from an empty retained candidate set. The supplied export has no raw model responses, per-candidate rejection diagnostics, token-limit traces or exception logs.

The local extraction prompt in `src/app/services/graph_index.py` (around lines 208-218) requests only explicit technical features, exact phrase/quote evidence from one chunk, and no inference from background wording; it permits an empty facts array when no feature is directly supported. This policy makes some review-scope zeros plausible. The observations below are human hypotheses about coverage under that policy, not retrospective proof of runtime causes.

## Reading-based classification

| Class | Documents | Count | Interpretation |
|---|---|---:|---|
| Content absent | none | 0 | Every zero-fact record has stored abstract text |
| Sparse generic stored source | D013 | 1 | Generic single sentence; conservative zero compatible with policy |
| Review/roadmap scope | D019, D023, D041, D048, D059, D084 | 6 | Topic vocabulary is present but paper-specific technical designs are weak or absent in the abstract |
| Explicit technical-feature candidates | D007, D064, D092 | 3 | High-priority manual candidates for controlled replay; underextraction plausible |
| Retrospective concrete methods, policy ambiguous | D015 | 1 | Concrete LIG methods present, but Account summarizes prior findings |

These classes partition the 11 records; they do not estimate recall on the remaining 89 documents. There is no evidence here to claim 11 extraction failures, 11 missing abstracts, or a token-limit/truncation cause. Likewise, a plausible conservative zero is not proof that all potential features were correctly excluded.

## Per-document findings

### D007 - Highly aligned SnO2 nanorods on graphene sheets for gas sensors

OpenAlex `W1996257604`; 848 characters; 1 chunk(s); priority: **high**; class: `concrete_feature_candidate`.

The abstract explicitly discloses a synthesized aligned SnO2-nanorod/graphene architecture, tunable nanorod diameter/density and measured H2S response. Several directly supported technical-feature candidates exist; zero facts is a coverage gap worth controlled replay. Conservative model selection or validation filtering is possible, but not observed as the actual cause.

Exact stored evidence: "Highly aligned SnO2 nanorods on graphene 3-D array structures were synthesized by a straightforward nanocrystal-seeds-directing hydrothermal method."

### D013 - Reduced graphene oxide/ZnO nanocomposite for application in chemical gas sensors

OpenAlex `W2318335082`; 147 characters; 1 chunk(s); priority: **low**; class: `sparse_generic_source`.

The only stored abstract sentence is generic background. The title names rGO/ZnO, but the extractor receives chunk text and should not infer a paper-specific feature from title-only specificity. Zero facts is compatible with the background-exclusion rule. The stored source is short, not absent; truncation at acquisition cannot be established from this export.

Exact stored evidence: "Coupling of graphene-based materials with metal oxide nanostructures is an effective way to obtain composites with improved gas sensing properties."

### D015 - Laser-Induced Graphene

OpenAlex `W4236825273`; 2679 characters; 3 chunk(s); priority: **medium**; class: `retrospective_methods_ambiguous`.

The Account contains concrete LIG production and morphology/surface-control methods across three complete chunks. These may be legitimate disclosed technical features, but wording is retrospective and broad. A zero result could reflect treating summarized prior findings as background. Audit policy must decide whether explicit reviewed methods qualify before scoring this as an extraction miss.

Exact stored evidence: "In 2014, using a commercial laser scribing system as found in most machine shops, a direct lasing of polyimide (PI) plastic films in the air converted the PI into 3D porous graphene, a material termed laser-induced graphene (LIG)."

### D019 - Graphene-based gas sensors

OpenAlex `W2076475450`; 569 characters; 1 chunk(s); priority: **low**; class: `review_scope_conservative_zero`.

A feature article states review scope and generic sensing-layer properties. It does not describe one concrete realized configuration or parameterized method in the abstract. Empty features is compatible with a strict explicit-disclosure policy; classifying topic from the same text remains possible.

Exact stored evidence: "The effects of the compositions, structural defects and morphologies of graphene-based sensing layers and the configurations of sensing devices on the performances of gas sensors will also be discussed."

### D023 - Biological and chemical sensors based on graphene materials

OpenAlex `W2138183388`; 861 characters; 1 chunk(s); priority: **low**; class: `review_scope_conservative_zero`.

The abstract enumerates reviewed sensor modalities and mechanisms, then promises comparative discussion. It has useful topic vocabulary but few specific disclosed designs. Conservative empty extraction is plausible; absence of stored content is ruled out.

Exact stored evidence: "This article critically and comprehensively reviews the emerging graphene-based electrochemical sensors, electronic sensors, optical sensors, and nanopore sensors for biological or chemical detection."

### D041 - A Review on Graphene-Based Gas/Vapor Sensors with Unique Properties and Potential Applications

OpenAlex `W2178763567`; 817 characters; 1 chunk(s); priority: **low**; class: `review_scope_conservative_zero`.

The review describes broad gas/vapor coverage and future/improvement proposals. Generic suggested hybrid structures and arrays are not necessarily technical features of a specific realized device. A conservative zero is plausible; whether proposed technical methods should count is a policy question.

Exact stored evidence: "Several possible methods to solve these problems are proposed, for example, conceived solutions, hybrid nanostructures, multiple sensor arrays, and new recognition algorithm."

### D048 - Science and technology roadmap for graphene, related two-dimensional crystals, and hybrid systems

OpenAlex `W2024227324`; 859 characters; 1 chunk(s); priority: **low**; class: `review_scope_conservative_zero`.

The roadmap abstract addresses research/industrial transition, sectors and nomenclature without a concrete sensor architecture or method. This is the clearest content-scope reason for an empty technical-feature set. Text is present and intact.

### D059 - Noble Metal Decorated Graphene-Based Gas Sensors and Their Fabrication: A Review

OpenAlex `W2570626050`; 899 characters; 1 chunk(s); priority: **low**; class: `review_scope_conservative_zero`.

The review describes a broad family of noble-metal/graphene hybrids and electron-transfer/junction mechanisms but does not name a particular metal, geometry or fabricated device in the abstract. Conservative zero is plausible; a looser disclosure policy might extract the generic hybrid family.

Exact stored evidence: "Specifically, noble metal decorated graphene-based novel structures were found to be extremely sensitive and selective owing to the synergistic effect of the compound configuration."

### D064 - Ultrafast and sensitive room temperature NH3 gas sensors based on chemically reduced graphene oxide

OpenAlex `W2038843379`; 841 characters; 1 chunk(s); priority: **high**; class: `concrete_feature_candidate`.

A specific pyrrole-reduction preparation method and IR-assisted sensor recovery are stated explicitly, together with measured NH3 response/kinetics. There are strong exact-span feature candidates. Treat zero as a high-priority underextraction hypothesis to replay, without attributing it to inference failure or validation behavior.

Exact stored evidence: "rGO, which was prepared via the reduction of graphene oxide by pyrrole, exhibited excellent responsive sensitivity and selectivity to ammonia (NH3) gas."

### D084 - Research Progress of Gas Sensor Based on Graphene and Its Derivatives: A Review

OpenAlex `W2854295798`; 1041 characters; 1 chunk(s); priority: **low**; class: `review_scope_conservative_zero`.

The abstract is a broad progress review and generic statement about composite candidates, preparation and performance. It does not supply a particular architecture/process. Conservative omission of background feature wording is plausible.

Exact stored evidence: "The emergence of new candidates including graphene, polymer and metal/metal oxide composite enhances the performance of gas detection significantly."

### D092 - Improving gas sensing properties of graphene by introducing dopants and defects: a first-principles study

OpenAlex `W1994481181`; 1191 characters; 1 chunk(s); priority: **high**; class: `concrete_feature_candidate`.

The DFT study explicitly investigates doped/defective graphene variants and reports differing adsorption/transport performance. These are directly supported modeled technical structures, not merely generic review scope. A high-priority coverage gap is plausible. Whether modeled designs qualify as disclosures should be made explicit; no logs prove a pipeline error.

Exact stored evidence: "The interactions between four different graphenes (including pristine, B- or N-doped and defective graphenes) and small gas molecules (CO, NO, NO(2) and NH(3)) were investigated by using density functional computations to exploit their potential applications as gas sensors."

## Recommended controlled follow-up

Start with D007, D064 and D092, plus D015 as a separate retrospective-method policy case. Replay only in an isolated analysis pipeline using the same frozen chunks, model version and prompt, retaining the raw candidate envelope and each validator decision. Compare whether candidates are absent from the model response or lost at validation; report those causes only after observing the corresponding trace. Include a review-scope control such as D048 or D019 to ensure the policy still rejects generic background.

Keep source retrieval, short-abstract enrichment, model extraction and validator behavior as distinct hypotheses. D013 would benefit from richer source content, but the current export alone cannot show whether its 147-character abstract is an upstream source limitation or acquisition behavior. Audit artifacts remain unchanged with respect to the production graph; no replay or reindexing was performed here.
