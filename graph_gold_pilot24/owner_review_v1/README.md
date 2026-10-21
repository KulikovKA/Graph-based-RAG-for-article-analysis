# Project-owner reviewed Gold release

The project owner explicitly confirmed in chat that they personally reviewed and approve all 24 current document annotations. This release records that attestation with `human_review_status=APPROVED`, `annotation_status=HUMAN_REVIEWED`, `primary_annotator=project_owner`, `review_date=2026-10-21` and `review_method=manual_owner_review`. `secondary_annotator` is null; no independent second review or agreement measurement is claimed.

The current dataset is `pilot24-owner-reviewed-gold-v1-20261021`, with standard `HUMAN_REVIEWED_GOLD_STANDARD`, AI-generated origin and `OWNER_APPROVED_FOR_EVALUATION` eligibility. This later manual-review decision supersedes the earlier unreviewed silver/draft eligibility for the active dataset. It does not rewrite the historical AI releases or their unreviewed status at that time.

`OWNER_DECISION.json` and the main adjudication journal record the owner's exact statement, review date and scope. `annotations/CURRENT_DATASET.json` is the active status pointer. Eighteen DEV/CALIBRATION reviewed files are in `annotations/gold/`. Six HOLDOUT reviewed files and their evidence, AI snapshots, patches, individual hashes and detailed validation stay in the existing private local storage outside the repository. Public reports expose only counts and review metadata for HOLDOUT.

The original AI files under `annotations/drafts/`, the frozen DEV namespace, baseline 0.3 and prior release commits remain intact. Nested labels receive review status metadata; all technical content is unchanged. All 23 abstention objects are preserved exactly and remain excluded from scored positive/negative labels. Their historical decision metadata is not silently rewritten.

The old JSON envelope was deliberately restricted to AI_DRAFT/NOT_REVIEWED. Separate `owner_review_*.schema.json` files change review metadata constraints only. Validation projects only those metadata fields back to the exact approved AI snapshots, checks equality, and reruns the immutable v1 ontology/source validators. Definitions, domain/range, qualifiers, polarity/modality and source spans are unchanged. The historical evaluation manifest is verified against its original Git commit; its AI-specific test now distinguishes the historical release from a subsequent reviewed Gold release.

```powershell
.venv\Scripts\python.exe graph_gold_pilot24/owner_review_v1/release.py
.venv\Scripts\python.exe -m unittest discover -s graph_gold_pilot24/owner_review_v1 -p test_owner_review.py
```

These commands validate the approved content; they do not conduct or simulate a human review. The record of manual review comes from the project owner's explicit chat confirmation. No architecture experiments are started by this promotion.
