# DEV completeness audit

All 12 DEV documents and all 78 frozen sentences were re-read in a distinct logical completeness pass. This is an AI self-audit, not measured recall or independent review. `sentence_audit.jsonl` records every sentence, its exact source text, retained assertion links and finding.

| Document | Sentences | Baseline assertions | v1.0 assertions | Finding |
|---|---:|---:|---:|---|
| D001 | 6 | 51 | 51 | Retain 84 days, 43.5 ppb theoretical LOD, and deformation metrics on their own results; room temperature attaches to gas detection. One collective process-group improvement, with explicit members; no three-by-four distribution. May provide/widespread monitoring remains HYPOTHETICAL. |
| D003 | 7 | 46 | 47 | Laser parameter optimization retained; layer position belongs to the component claim. NO/NO2 response and LOD values remain distinct. Added one joint explanation of 30% stretch; individual design factors are involved components of that account. 90% RH belongs to moisture resistance; demonstrated monitoring and breath classification remain actual uses. |
| D004 | 8 | 18 | 24 | Decreased oxygen ratio stays a bearer-property trend associated with phase appearance; with does not establish phase-causes-ratio. Only direct graphene->energy transport and treatment->evaporation facilitation; no transitive shortcut. 24.7 response, 1 ppm NO2 and 150 °C share the response assertion. Proposed generation->formation CAUSES and one collective junction->sensitivity EXPLAINS. ASSERTED partial defect contribution outside the previous suggest-that clause; no fraction. |
| D010 | 7 | 99 | 99 | Each enumerated nanocomposite is explicitly said to be synthesized and used; compositional components stay within its own formula. Awkward source best remains only unspecified overall comparison, not a fabricated numerical ranking. Ordered 9:1:5:5 ratio remains exactly as source; material composition unchanged. 96%/200 ppm, 30-70%RH, R²=0.998 and 4.1 ppm keep separate outcome attachments. Humidity independence does not establish a quantitative zero slope. All mechanism, layer location and conductivity-type assertions stay PROPOSED; electronic layers/junctions are MORPHOLOGY. |
| D060 | 4 | 10 | 12 | NO2 is MATERIAL dopant, NH3 is ANALYTE; improvement is evaluative. Doped and before-doping LOD values remain distinct comparison values. Added adsorption->hole concentration increase->sensitivity explanation; repaired Q5 head to preserve the intermediate parameter. |
| D078 | 9 | 24 | 39 | Exposure decreases current; magnitude of the decrease depends on amine count. Material mechanism admitted. Highest scopes outcomes, not component/analyte membership. Calculated support retained as provenance; supported result ASSERTED. Impurities increase decrease magnitude, not electric current; explanatory response link retains NO2/SO2 scope. Retain absent strong NH3 interaction and combined electronic effects. Added current increase and mobility decrease with one collective full explanation, no quantitative cancellation. Negative HAS_PERFORMANCE targets base response. Top dopant produces n-channel induction; no fabricated vertical gate-stack components. Could be used remains HYPOTHETICAL, with subppq and mixture scope. |
| D035 | 4 | 25 | 15 | Retired the unlicensed 4x4 use grid; add one DFT process acting on explicitly enumerated surface group with gas scope. Calculated improvement of adsorption energy/selectivity remains evaluative in source terms, not a signed energy increase inference. Explicit significant property change added as direction unspecified, with calculation/comparison scope. Can be sensitive/selective remains prospective; no experimental sensor manufacture inferred. |
| D092 | 7 | 13 | 19 | Potential device/material uses remain hypothetical. One group-to-group dependence replaces four unresolved candidate cross-product links. Stronger adsorption remains a calculated comparison, not measured sensor selectivity. Separate defective-graphene CO/NO/NO2 result and B-doped-graphene NH3 result. Interaction induces electronic-change event; unknown direction retained. Two-order sensitivity advantage is calculated; calculation does not itself mean proposed. Could be improved stays HYPOTHETICAL. |
| D017 | 7 | 29 | 28 | Application list explicitly governs the material class; structural and property types remain distinct. Potential gas sensing and stated surface properties retained; no new causal law inferred. Review discourse about mechanisms and device types does not name a device-specific mechanism; retired generic HAS_MECHANISM. Explicit material application list can distribute the common gas-sensing use; GO/rGO and related classes remain distinct. |
| D038 | 5 | 16 | 17 | Admit material synergy mechanism and preserve review-level support. Hybridization to improve is purpose PROPOSED; composition not generalized to every named oxide combination. Insufficient sensitivity/response rate and long recovery are limited to some cases. Retain facilitation of adsorption/diffusion and joint explanatory features in qualifier; no independent sufficiency by each feature. Synthesis/assembly/application review claims remain general method/use relations, without invented parameter values. |
| D026 | 7 | 12 | 19 | One negative MEETS_REQUIREMENT to ALL/noise-and-signal bundle, no independent negative member edges. MXenes possess both required traits; add positive joint satisfaction plus conductivity->noise and surface->signal explanations. 50-100 ppb is VOC LOD range at room temperature. Low noise explains SNR; two orders and other-2D-material comparison remain on SNR result. |
| D024 | 7 | 15 | 20 | Calculated permeability/selectivity retain designed-pore scope. Nitrogen-functionalized pore result remains separate from hydrogen-passivated pore. MORPHOLOGY pore->width admitted with literal 2.5 A; width explains gas-specific barriers. Bulk solubility/diffusivity collectively dominate traditional membrane transport; use EXPLAINS+dominant. Suggest scopes pore superiority, not the background where-clause. Neutral selectivity/diffusivity tuning replaces unsupported optimality; proposed techniques remain prospective. Explicit membrane role and gas separation use remain PROPOSED. Impact wording insufficient for fuel-cell/gas-sensor use; keep Q6/Q7 and carbon-sequestration audit abstention. No DEVICE tail expansion. |

## Vocabulary sufficiency and uncovered statements

Five predicates are added because existing meanings would lose distinct DEV facts: CAUSES, EXPLAINS, CHANGES_PARAMETER, DEPENDS_ON and MEETS_REQUIREMENT. INCREASES and DECREASES are one signed parameter predicate; direction is compulsory. DOMINATES is EXPLAINS with contribution=dominant. HAS_MECHANISM admits MATERIAL, HAS_PROPERTY admits MORPHOLOGY, and HAS_MEMBER admits the explicit morphology/mechanism bundles and mixed requirement members. USED_FOR is not extended to DEVICE tails.

D024-Q6 and D024-Q7 remain INSUFFICIENT_EVIDENCE: possible impact on fuel cells/gas sensors is weaker than a use claim. The same backward rule retires carbon-sequestration use, retained as V1-D024-A1 audit abstention. These are semantic insufficiency, not a reason to invent a relation. The rubric still represents explicit proposed membrane/gas-separation use.

D017 review organization (we discuss mechanisms and introduce devices) does not identify a device-specific mechanism. This is a documented discourse exclusion, not a missing relation type. D035 the sixteen material-by-gas uses are replaced by one group study claim: a computational investigation is not independent demonstration of every pair. D024 neutral parameter tuning is captured by CHANGES_PARAMETER with unspecified direction; no new optimum relation is needed.

Parameter changes of known sign (D060 carrier increase, D078 current and mobility changes) use direction. D004 a bearer oxygen-ratio trend with associated phase appearance remains HAS_PROPERTY+trend because with does not name a causal factor. D010 humidity independence retains its humidity range on the performance claim; a numerical unchanged response or derivative cannot be inferred. Unspecified electronic change (D035/D092) is supported without an invented sign.

Qualitative source evaluations, first-principles provenance, comparative baselines, local conditions, source-reported limitations and collective explanations are supported. The pilot does not encode full equations, quantitative causal effect sizes, independent sensor instances absent source identity, or vague impact as concrete deployment. These omissions are acceptable because the abstracts do not establish those facts, and no unsupported labels are manufactured.

## Counts

```json
{
  "documents": 12,
  "entity_kinds": 12,
  "relation_types": 23,
  "historical_questions": 20,
  "historical_candidates": 26,
  "question_decisions": {
    "ACCEPT": 14,
    "MAP_TO_EXISTING": 4,
    "INSUFFICIENT_EVIDENCE": 2
  },
  "candidate_decisions": {
    "ACCEPT": 19,
    "MAP_TO_EXISTING": 5,
    "INSUFFICIENT_EVIDENCE": 2
  },
  "remaining_unresolved_historical_questions": 2,
  "additional_audit_abstentions": 1,
  "baseline_mentions": 573,
  "final_mentions": 589,
  "baseline_assertions": 358,
  "final_assertions": 390,
  "added_assertions": 51,
  "retired_assertions": 19,
  "semantically_corrected_existing_assertions": 23,
  "semantic_corrected_assertion_ids": [
    "2018438e-1d19-546f-b80e-407f376b30d2",
    "24d25d7e-d78d-5f56-a388-097391da895a",
    "32ac6681-cdde-54f6-b527-4d5ae807fa5b",
    "3d2b7e9b-c343-5035-a706-e0c1a3850765",
    "538bea3f-00a1-5a2e-bb45-f18e2fb8e326",
    "8598c2fa-3d68-5b91-be12-2f75063bc757",
    "91304995-e92c-5cc8-887e-cdedf83fa2e7",
    "951873ee-c305-57fd-8a26-a5c0d054aa82",
    "953faa82-6f30-5a57-9dde-78ac498c64ac",
    "97b648e5-df0b-5491-a2f5-646b71948210",
    "999a2edf-7f4c-5538-91e7-2a931a28a429",
    "a8d58466-b814-517d-8dcf-473a61c9a129",
    "abd3e3c2-17f4-50c6-a6cf-1276770c577a",
    "ac8268e2-b445-509f-a599-c6e8d0214be9",
    "bd0ed1cc-3055-5092-92c7-48f7054136a7",
    "bfb537f4-4f79-53cc-8eca-a44f2bcb36ce",
    "c0300117-f013-5899-a6f6-bb606becfb42",
    "c4757807-3d44-5601-82cc-6eab1ded91c6",
    "cc13c2b3-1084-51ae-88bd-48ef3f1ca346",
    "dbc6e834-cfce-5e44-97eb-ca7af1388265",
    "e28e0a80-20d8-5d27-a9f4-eec5a44f0828",
    "e7eca2f8-6c06-51ab-bc37-538d43d66c48",
    "fdcd0d37-ff05-512a-b803-5cf3434beaef"
  ],
  "metadata_only_existing_assertions": 316,
  "baseline_unique_canonical_triples": 327,
  "final_unique_canonical_triples": 359,
  "final_relation_counts": {
    "ACTS_ON": 13,
    "CAUSES": 3,
    "CHANGES_PARAMETER": 8,
    "DEPENDS_ON": 2,
    "DETECTS": 13,
    "EXPLAINS": 11,
    "FABRICATED_BY": 14,
    "FACILITATES": 3,
    "FUNCTIONS_AS": 3,
    "HAS_COMPONENT": 57,
    "HAS_MECHANISM": 6,
    "HAS_MEMBER": 44,
    "HAS_MORPHOLOGY": 17,
    "HAS_PERFORMANCE": 52,
    "HAS_PROPERTY": 52,
    "IMPROVES": 7,
    "INTEGRATED_IN": 1,
    "LOCATED_IN": 2,
    "MECHANISM_INVOLVES": 9,
    "MEETS_REQUIREMENT": 2,
    "OPTIMIZES": 1,
    "USED_FOR": 47,
    "USES_MATERIAL": 23
  },
  "human_gold_documents": 0,
  "final_human_ontology_approved": false
}
```

All historical 20 questions receive a decision; 2 remain unresolved from genuine insufficient evidence. One additional backward-audit abstention is kept separately, so the total unresolved cases are 3. No original candidate is silently removed from the journal. Structural checks are reported separately from this semantic claim.
