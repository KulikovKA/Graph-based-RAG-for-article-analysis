# Evaluation annotation under the approved pilot ontology

The current schema status is in `../ontology/CURRENT_STATUS.json`; the user decision and date are in `../ontology/approvals/pilot24-ontology-v1.0.json`. The original technical-freeze files remain unchanged, including their historically pending status. Effective approval applies to the schema only.

`validation.py` checks approval and immutable hashes, then reuses the frozen semantic/grounding checks through the documented provenance adapter. `evaluation_annotation.schema.json` differs from the frozen annotation envelope only in metadata described in `TECHNICAL_ISSUES.md`; ontology definitions and qualifiers are unchanged. `validate_all.py` validates all 24 current drafts and writes public counts/status plus a private HOLDOUT details report.

```powershell
.venv\Scripts\python.exe graph_gold_pilot24/evaluation_v1/validate_all.py
.venv\Scripts\python.exe -m unittest discover -s graph_gold_pilot24/evaluation_v1 -p test_evaluation.py
```

CALIBRATION was reviewed first, then HOLDOUT. `calibration/baseline_0.3/` preserves the six original draft files. `sources/`, `drafts/`, `patches/`, `decisions/`, `semantic_changes/`, `sentence_audit/` and `reports/` preserve the new annotations and lineage. Top-level RFC6902 replacements replay exactly from parsed baseline JSON to final JSON. Baseline bytes and resulting file hashes are separately pinned. Rerunning `reannotate_calibration.py` uses those baselines, not current drafts, and is deterministic.

The corresponding HOLDOUT baselines, sources, scripts, decisions, patches and reports live entirely in the existing private local storage, outside the repository. No HOLDOUT labels or label-derived technical examples are embedded in public scripts. Public REPORT.md/REPORT.json include only counts/status for those documents.

`QUALIFIER_NOT_IN_FROZEN_V1` cases preserve full original numerical/contextual data. Accepted base claims may still cite the same exact sentence while the unsupported typed qualifier remains abstained. Existing controlled fields are used only for their documented meaning. The fixed ontology is not broadened to improve evaluation coverage. Review-topic discourse is excluded when it does not identify a technical relation; absence of annotation never means a negative label.

Run the human procedure in `HUMAN_REVIEW_PROTOCOL.md` before forming Gold Dataset. All current annotations remain AI drafts, without independent human verification. No experiment work was started.
