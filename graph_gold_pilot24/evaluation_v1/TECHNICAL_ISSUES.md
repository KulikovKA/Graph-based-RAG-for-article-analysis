# Frozen v1.0 implementation issues, without ontology changes

V1-TECH-001 (2026-10-21): the frozen annotation envelope permits all three splits but hardcodes `source_context.interpretation_basis = AI_DEV_SOURCE_REVIEW`. The frozen validator additionally refuses non-DEV inputs. These are implementation/provenance limitations, not evidence for changing relation semantics. Reporting CALIBRATION/HOLDOUT as reviewed on DEV would be false.

This evaluation workflow uses an explicitly separate metadata envelope, `pilot24-evaluation-envelope-1.0`, with `interpretation_basis = AI_FROZEN_ONTOLOGY_SOURCE_REVIEW` and an outer provenance object recording the actual split, actor and approval record. Its schema is derived from the byte-pinned frozen annotation schema with only that provenance literal changed and the additional metadata required. The 23 predicates, entity kinds, endpoints, qualifier definitions/constraints, evidence requirements, polarity and modality are identical.

For reuse of the immutable DEV validator, the evaluation adapter validates the true split/source identity first, then makes a temporary in-memory compatibility projection of only the split labels and provenance literal. It never writes that projection, never changes text, spans, relations, qualifiers or identities, and never changes frozen files. Reports identify this adapter explicitly. The original DEV workflow continues to validate byte-identical frozen DEV drafts with its original entrypoint.

Candidate for a future implementation release: parameterize allowed splits and provenance actor in the validator/envelope. No v1.0 ontology revision is made or implied. Other evidence-specific gaps belong in the appropriate split's abstention log; HOLDOUT details remain private.
