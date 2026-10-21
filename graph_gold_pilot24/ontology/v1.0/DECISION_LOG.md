# DEV adjudication decision log

Actor: AI. Final human ontology approval: false. Annotation human review: NOT_REVIEWED. This log records design adjudication, not gold approval. The immutable input snapshot retains every original question, candidate and evidence. Machine records are in `adjudication_decisions.jsonl`.

## Historical 19 → 20 reconciliation

The 0.3 freeze reports 19 unresolved DEV questions. The isolated current DEV review bundle contains 20 unique question IDs and 26 candidate assertions. D078-Q9 is the later semantic self-audit addition about combined current-increase/mobility-decrease effects. The other 19 questions account for the earlier set; Q9 is retained and explicitly decided here. The historical 0.3 report is not edited or retroactively restated as 20. This explanation follows the supplied question provenance and old count; this isolated task does not reopen prior curation scripts or evaluation reports.

| Question | Original proposal | Decision | Candidates | Result assertions |
|---|---|---|---:|---|
| D004-Q4 | CAUSES | ACCEPT | 1 | `fda0b6f7-50d4-5329-9479-9586a95ec805` |
| D004-Q5 | EXPLAINS | ACCEPT | 3 | `158f5df0-7e4e-53ec-b78f-2a7e22bb9e93` |
| D004-Q6 | EXPLAINS | ACCEPT | 1 | `f31d83f7-ee09-59d9-96b9-5f9f0f688391` |
| D024-Q4 | HAS_PROPERTY | ACCEPT | 1 | `2b152c54-af03-58e1-bc64-be5181217d74` |
| D024-Q5 | DOMINATES | MAP_TO_EXISTING | 2 | `70a4b64c-9e79-5b6e-b333-540da4bf1e1f` |
| D024-Q6 | USED_FOR | INSUFFICIENT_EVIDENCE | 1 | UNRESOLVED |
| D024-Q7 | USED_FOR | INSUFFICIENT_EVIDENCE | 1 | UNRESOLVED |
| D026-Q4 | MEETS_REQUIREMENT | ACCEPT | 1 | `353bda66-bf30-57b4-8b2b-9cee1eff65a0` |
| D026-Q5 | EXPLAINS | ACCEPT | 1 | `7bc87ce6-4274-5866-be12-cdca561d6f83` |
| D038-Q4 | HAS_MECHANISM | ACCEPT | 1 | `75296514-e08f-5f00-a2c5-ec5dd1e337d9` |
| D060-Q4 | INCREASES | MAP_TO_EXISTING | 1 | `3474a0cd-e488-53f9-9dd9-82ace9d3f4ec` |
| D060-Q5 | EXPLAINS | ACCEPT | 1 | `5cb446fe-0bd9-57b0-8629-ac9a4d4885c0` |
| D078-Q4 | CAUSES | MAP_TO_EXISTING | 1 | `4f408a6d-fde0-5e98-8d5a-cee46da0a4f8` |
| D078-Q5 | DEPENDS_ON | ACCEPT | 1 | `943d8572-c7a6-5cd3-b884-76eb38015c23` |
| D078-Q6 | HAS_MECHANISM | ACCEPT | 1 | `655f11c5-b72b-5aff-b49c-21669f45ff63` |
| D078-Q7 | INCREASES | MAP_TO_EXISTING | 1 | `51bcace7-7f33-56b2-a1e4-a64bfa26698d` |
| D078-Q8 | HAS_MECHANISM | ACCEPT | 1 | `beda40e2-e47e-56be-ab5d-84dfe26aca27` |
| D078-Q9 | HAS_MECHANISM | ACCEPT | 1 | `4000ae68-924b-5424-964f-ce95c52c62b8` |
| D092-Q4 | DEPENDS_ON | ACCEPT | 4 | `0d99a982-06b2-5950-9e61-332ddccba96b` |
| D092-Q5 | CAUSES | ACCEPT | 1 | `310627ec-9ac3-5259-bc1c-9c37afc244aa` |

## D004-Q4

Admit CAUSES for explicitly proposed event production. Keep generation and formation as PROCESS; do not substitute junction objects.

Candidate links: `fda0b6f7-50d4-5329-9479-9586a95ec805`.

Exact evidence: `eb47e91a-4c35-4de7-96a3-f141eea0a6cf` [0,321).

> We suggest that the generation of SnO x nanoparticles and the SnO x phase in the matrix results in the formation of SnO 2 /SnO 2 homojunctions, SnO 2 /SnO x ( x < 2) heterojunctions, and SnO 2 /graphene heterojunctions, which are responsible for the excellent sensitivity of the graphene–SnO 2 nanocomposites to NO 2 gas.


## D004-Q5

Admit EXPLAINS with MORPHOLOGY head. The plural which refers to the junction list collectively; replace three separately sufficient-looking candidates by one group explanation. We suggest remains PROPOSED.

Candidate links: `5429b6bb-6fc1-55ed-9413-2aca036e3617`, `6cd06818-0052-51ba-90d5-71f1f8c0ece6`, `5ff43ec8-eef5-5032-9612-5300c3c627fb`.

Exact evidence: `eb47e91a-4c35-4de7-96a3-f141eea0a6cf` [0,321).

> We suggest that the generation of SnO x nanoparticles and the SnO x phase in the matrix results in the formation of SnO 2 /SnO 2 homojunctions, SnO 2 /SnO x ( x < 2) heterojunctions, and SnO 2 /graphene heterojunctions, which are responsible for the excellent sensitivity of the graphene–SnO 2 nanocomposites to NO 2 gas.


## D004-Q6

The next independent sentence says is also partly responsible. The prior We suggest that syntactically scopes S7, not the declarative S8; classify S8 ASSERTED, with contribution=partial and no invented numerical fraction. This AI scope judgement remains subject to human review.

Candidate links: `f31d83f7-ee09-59d9-96b9-5f9f0f688391`.

Exact evidence: `eb47e91a-4c35-4de7-96a3-f141eea0a6cf` [322,478).

> In addition, the generation of surface Sn interstitial defects is also partly responsible for the excellent NO 2 sensing performance observed in this study.


## D024-Q4

Extend HAS_PROPERTY to MORPHOLOGY for the width of the explicit all-hydrogen-passivated pore. Preserve the literal unit A; no silent angstrom conversion.

Candidate links: `2b152c54-af03-58e1-bc64-be5181217d74`.

Exact evidence: `8c66a2f4-bc1a-4135-b4ed-059f62c24390` [288,518).

> We find extremely high selectivity on the order of 10(23) for H(2)/CH(4) for an all-hydrogen passivated pore whose small width (at 2.5 A) presents a formidable barrier (1.6 eV) for CH(4) but easily surmountable for H(2) (0.22 eV).


## D024-Q5

Do not add DOMINATES. EXPLAINS with contribution=dominant retains its distinct strength and collective bulk-solubility/diffusivity scope in traditional membranes. Two independent sufficient causes are not asserted.

Candidate links: `541f400b-e5db-5288-833d-1541fb4ef51b`, `1a715f9e-771c-579e-9921-87ef735c53d6`.

Exact evidence: `8c66a2f4-bc1a-4135-b4ed-059f62c24390` [519,719).

> These results suggest that these pores are far superior to traditional polymer and silica membranes, where bulk solubility and diffusivity dominate the transport of gas molecules through the material.


## D024-Q6

Could have widespread impact names possible application areas but does not establish a material-to-device use or fabricated component. Keep the candidate UNRESOLVED; do not widen USED_FOR to DEVICE tails from this evidence.

Candidate links: `dd69b6eb-2e3f-5f03-8c95-e89e926e61fa`.

Exact evidence: `8c66a2f4-bc1a-4135-b4ed-059f62c24390` [988,1121).

> Hence, we propose using porous graphene sheets as one-atom-thin, highly efficient, and highly selective membranes for gas separation.

Exact evidence: `6a14ebc5-5021-4e98-9eda-0b99d7267b5c` [0,152).

> Such a pore could have widespread impact on numerous energy and technological applications; including carbon sequestration, fuel cells, and gas sensors.


## D024-Q7

Could have widespread impact names possible application areas but does not establish a material-to-device use or fabricated component. Keep the candidate UNRESOLVED; do not widen USED_FOR to DEVICE tails from this evidence.

Candidate links: `4eef7510-4b15-54b6-b8b3-98d6b1f80b0f`.

Exact evidence: `8c66a2f4-bc1a-4135-b4ed-059f62c24390` [988,1121).

> Hence, we propose using porous graphene sheets as one-atom-thin, highly efficient, and highly selective membranes for gas separation.

Exact evidence: `6a14ebc5-5021-4e98-9eda-0b99d7267b5c` [0,152).

> Such a pore could have widespread impact on numerous energy and technological applications; including carbon sequestration, fuel cells, and gas sensors.


## D026-Q4

Admit MEETS_REQUIREMENT for an explicit requirement bundle, repairing the candidate tail from only low noise to two requirements. NEGATIVE with joint_requirement=all means not both simultaneously; neither individual failure is inferred.

Candidate links: `353bda66-bf30-57b4-8b2b-9cee1eff65a0`.

Exact evidence: `5a1139f9-9bf1-4665-96e1-c15a6477ded6` [263,438).

> To obtain high sensitivity, two requirements need to be simultaneously satisfied: (i) low electrical noise and (ii) strong signal, which existing sensor materials cannot meet.


## D026-Q5

The source led to attribution directly links low-noise PROPERTY to SNR PERFORMANCE; it is not a possession statement or process improvement.

Candidate links: `7bc87ce6-4274-5866-be12-cdca561d6f83`.

Exact evidence: `5a1139f9-9bf1-4665-96e1-c15a6477ded6` [800,957).

> Also, the extremely low noise led to a signal-to-noise ratio 2 orders of magnitude higher than that of other 2D materials, surpassing the best sensors known.


## D038-Q4

MATERIAL domain extension is independently supported by the explicit synergetic effects of the two components in this DEV review. A material may bear a mechanism without inventing a DEVICE mention.

Candidate links: `75296514-e08f-5f00-a2c5-ec5dd1e337d9`.

Exact evidence: `fb767df1-8f61-4334-89e7-29c1cdcf5364` [0,198).

> Graphene/metal oxide-based materials have been demonstrated as promising candidates for gas sensing applications due to the enhanced sensing performance and synergetic effects of the two components.


## D060-Q4

The INCREASES proposal is represented by the newly canonical CHANGES_PARAMETER plus required direction=increase. This is a physical carrier increase and never IMPROVES by definition.

Candidate links: `3474a0cd-e488-53f9-9dd9-82ace9d3f4ec`.

Exact evidence: `006deffa-1906-4677-942b-2a29bd47046b` [496,745).

> Electrical characterization and Raman spectroscopy measurements on graphene field-effect transistors show that adsorption of NO2 molecules significantly increases hole concentration in graphene, which results in the observed sensitivity enhancement.


## D060-Q5

Admit EXPLAINS, repairing the candidate head from adsorption to hole concentration in its explicitly increased state. This preserves the stated intermediate chain and avoids a direct adsorption-to-sensitivity shortcut.

Candidate links: `5cb446fe-0bd9-57b0-8629-ac9a4d4885c0`.

Exact evidence: `006deffa-1906-4677-942b-2a29bd47046b` [496,745).

> Electrical characterization and Raman spectroscopy measurements on graphene field-effect transistors show that adsorption of NO2 molecules significantly increases hole concentration in graphene, which results in the observed sensitivity enhancement.


## D078-Q4

Use CHANGES_PARAMETER(direction=decrease) for the specific current effect. Add an exact current parameter mention; the original current-decrease state remains available. No separate DECREASES predicate is needed.

Candidate links: `4f408a6d-fde0-5e98-8d5a-cee46da0a4f8`.

Exact evidence: `8e528f95-22fc-4b9a-8b16-90391b584bc3` [233,429).

> The exposure of the n-doped graphene to oxidizing gases such as NO 2 leads to a current decrease that depends strongly on the number of amine functional groups in various types of ethylene amines.


## D078-Q5

Admit DEPENDS_ON for the explicitly stated dependence of the current-decrease magnitude on amine-group count. No sign or functional law is inferred.

Candidate links: `943d8572-c7a6-5cd3-b884-76eb38015c23`.

Exact evidence: `8e528f95-22fc-4b9a-8b16-90391b584bc3` [233,429).

> The exposure of the n-doped graphene to oxidizing gases such as NO 2 leads to a current decrease that depends strongly on the number of amine functional groups in various types of ethylene amines.


## D078-Q6

Extend HAS_MECHANISM to MATERIAL: the material is the grammatical bearer of sensing performance and the electrostatic explanation. Preserve target NO2 and the stated behavior scope.

Candidate links: `655f11c5-b72b-5aff-b49c-21669f45ff63`.

Exact evidence: `8e528f95-22fc-4b9a-8b16-90391b584bc3` [430,744).

> Graphene doped with diethylenetriamine (DETA) exhibits the highest response, recovery, and long-term sensing stability to NO 2, with an average detection limit of 0.83 parts per quadrillion (ppq, 10 –15 ), due to the attractive electrostatic interaction between electron-rich graphene and electron-deficient NO 2 .


## D078-Q7

Map INCREASES to CHANGES_PARAMETER(direction=increase) on the magnitude of current decrease. The current itself decreases; do not reverse its physical sign.

Candidate links: `51bcace7-7f33-56b2-a1e4-a64bfa26698d`.

Exact evidence: `8e528f95-22fc-4b9a-8b16-90391b584bc3` [843,1033).

> In addition, gas molecules on the n-channel graphene provide charged impurities, thereby intensifying the current decrease for an excellent response to oxidizing gases such as NO 2 or SO 2 .


## D078-Q8

The MATERIAL domain extension permits the explicitly absent strong interaction. Keep NEGATIVE polarity restricted to NH3 and DETA-doped graphene; no global absence of interaction is inferred.

Candidate links: `beda40e2-e47e-56be-ab5d-84dfe26aca27`.

Exact evidence: `509195ce-f818-487d-8196-eb0511b0acaf` [0,232).

> On the contrary, absence of such a strong interaction between NH 3 and DETA-doped graphene and combined effects of current increase by n-doping and mobility decrease by charged impurities result in a completely no response to NH 3 .


## D078-Q9

The later self-audit question identifies a real additional material-domain mechanism candidate. Admit the combined current/mobility effects, scoped to NH3. No quantitative cancellation or independently sufficient cause is claimed; the whole explanation also includes absent strong interaction.

Candidate links: `4000ae68-924b-5424-964f-ce95c52c62b8`.

Exact evidence: `509195ce-f818-487d-8196-eb0511b0acaf` [0,232).

> On the contrary, absence of such a strong interaction between NH 3 and DETA-doped graphene and combined effects of current increase by n-doping and mobility decrease by charged impurities result in a completely no response to NH 3 .


## D092-Q4

Admit DEPENDS_ON but preserve both coordinated lists as groups. All four candidate links map to one collective dependence; the abstract does not independently establish every pair in their Cartesian product.

Candidate links: `47c71199-9ff3-5168-b7e7-6f53d397b35e`, `f4006790-5d34-5252-9877-bde6d71b1a5d`, `8ead1e1c-2023-5a16-983c-6922908324ae`, `0df7553f-34cc-5de1-94de-cca1f9ccdcb7`.

Exact evidence: `8c72db49-9f37-4151-a3be-46a88d5af916` [275,452).

> The structural and electronic properties of the graphene-molecule adsorption adducts are strongly dependent on the graphene structure and the molecular adsorption configuration.


## D092-Q5

Induce explicitly asserts production of a change event. Keep MECHANISM -> PROCESS with the target electronic parameter stated in a qualifier; the direction/magnitude is not given.

Candidate links: `310627ec-9ac3-5259-bc1c-9c37afc244aa`.

Exact evidence: `8c72db49-9f37-4151-a3be-46a88d5af916` [736,889).

> Meanwhile, the strong interactions between the adsorbed molecules and the modified graphenes induce dramatic changes to graphene's electronic properties.

## Approval separation

Earlier user Q1–Q6 instructions are design constraints, not independent annotation review. The three D004 decisions and two D060 decisions are implemented with explicit AI source interpretation. Other cases are AI adjudications authorized by the task. Technical freeze can be automatic; final human ontology approval remains false, and human gold remains 0/12 DEV.
