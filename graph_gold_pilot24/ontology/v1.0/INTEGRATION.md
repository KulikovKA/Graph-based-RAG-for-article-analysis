# Local integration and verification

The authoritative specification is `ontology.json`; `annotation.schema.json` constrains the retained `graph-gold-pilot-v0` storage envelope. The ontology identity is `pilot24-ontology-v1.0`, independently of that envelope name. `ontology.schema.json` checks the specification itself. `build_schemas.py` deterministically generates both schemas from the preserved envelope and the DEV ontology.

All 12 DEV drafts are published both in `dev_drafts/` and in the existing `annotations/drafts/` paths. Their bytes match. The current `annotations/reviews/relation_vocabulary.json` is a v1 adapter with explicit approval states. The original 0.3 vocabulary, including its damaged historical descriptions, remains byte-preserved under `../baselines/pilot24-auto-freeze-0.3/`; its original Git version also remains at the baseline commit. The old root annotation schema and old freeze report are unchanged. Twenty AI decision records were appended to the existing adjudication journal without changing its four historical records. New DEV decisions are also immutable in this directory. Old combined campaign reports/questions remain historical 0.3 records; they are not v1 results and were not regenerated using evaluation inputs.

`integration_report.json` records the promoted DEV hashes and verifies the historical baseline hashes. This namespace disables Git newline conversion because some original byte-hashed snapshots contain CRLF; newly generated artifacts use explicit LF. This avoids a different hash after checkout.

Run from the repository root, after the technical seal exists:

```powershell
.venv\Scripts\python.exe graph_gold_pilot24/validate_annotations.py
.venv\Scripts\python.exe -m unittest discover -s graph_gold_pilot24 -p test_ontology_v1.py
```

The default validator loads only the fixed DEV snapshot and its 12 drafts. It checks schema, domain/range, membership pairs, controlled qualifiers, evidence offsets/hashes, attachment, identity constraints, versions, recorded AI source interpretation and every sealed artifact/tool hash. Tests also verify all 23 ontology examples against actual accepted DEV assertions, complete question/candidate inventory, promoted-copy equality, and deliberately malformed annotations. `test_report.json` records the test result; `validation_report.json` records the 12 document results. These checks do not establish physical truth, measured annotation recall or independent human review.

The explicit `--ontology legacy-0.3` route retains compatibility with historical annotations. It can access the old complete campaign and is outside this DEV-only design workflow; it was not run here. Validation under v1 currently refuses evaluation inputs. Future CALIBRATION/HOLDOUT work must use the frozen vocabulary in a separately scoped workflow, retaining abstentions instead of silently changing this ontology.

Reproduce semantic artifacts in a separate checkout using the command in `ANNOTATION_RUBRIC.md`. `REPRODUCIBILITY_CHECK.json` records two byte-identical semantic builds and exact replay of all 12 lossless patches. The patch includes the ontology hash. Repository integration then runs `build_schemas.py`, `integrate_dev.py`, and the DEV validator/tests. Integration refuses to republish after `FREEZE_MANIFEST.json` exists.

Two local commits avoid a self-referential Git hash. First commit all final content and passing reports. Then run `freeze_ontology_v1.py`: it verifies that all sealed files/tooling exactly match their Git blobs and records that content commit. Commit only the resulting manifest next. The manifest pins the content SHA, ontology/schema SHA-256, source revisions/chunks, decision history, hashes and approval states. No push is part of this workflow.

Individual user schema constraints, AI adjudication, technical freeze, final human ontology approval, and human label review remain separate. The final two states are PENDING and NOT_REVIEWED respectively; human gold is zero. Parent-context exposure and the historical failed 0.3 freeze write followed by calibration display are explicitly documented in `DEV_INPUT_ISOLATION.json`, the ontology provenance and the freeze manifest. A fresh DEV-only semantic context limits additional exposure, but cannot prove end-to-end independence or undo baseline contamination.
