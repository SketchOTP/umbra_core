# UMBRA-D-013H-R1 — V2 First-Failure / Zero-Recovery Evidence Hardening

Status: `NON_FORMAL_TEST`

This dossier records the bounded D-013H-R1 harness/evidence patch. It closes
one evidence-lifecycle defect without changing the V2 scientific semantics,
organism code, thresholds, formal configuration, or historical evidence.

The campaign-owned V2 evaluator trace now begins with one durable,
identity-bound `EVALUATOR_INIT` record. A campaign may therefore terminate
before any recovery evaluation and still publish a valid init-only trace.
Replacement workers ignore that lifecycle record as an episode and restore
only actual recovery-evaluation rows.

Closeout preserves an existing scientific first failure. A later read-only or
publication problem is recorded separately as a secondary evidence finding;
when no earlier failure exists, the publication problem becomes the terminal
fail-closed result.

No formal P0 was launched, no formal baseline or tag was created, and no
formal scientific evidence was generated.
