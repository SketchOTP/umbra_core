# UMBRA-D-014G1 — D-014F Prospective Proposal Artifact Recovery / Replay Qualification

- Status: terminal; verdict: `D014G1_D014F_ARTIFACT_UNRECOVERABLE`
- Baseline: `5609414259e99aae5f3e932c7181f1107130c922`
- Parent: D-014G fail-closed shadow boundary
- Mode: non-formal, evidence-forensics and replay qualification only

## Objective

Determine whether the exact frozen D-014F `RegulatoryOpportunity` mechanism
can be reconstructed reproducibly from retained evidence and specification.
Do not design a new mechanism, infer missing semantics, or promote D-013AO.

## Required sequence

1. Inventory the complete D-014F Atlas dossier and any exact associated
   repository/history artifacts.
2. Classify every behaviorally relevant generator rule as exact, uniquely
   derivable, ambiguous, or missing.
3. Stop as `D014G1_D014F_ARTIFACT_UNRECOVERABLE` if any required rule is
   ambiguous or missing.
4. Only if all rules are exact/uniquely derivable may a non-production replay
   artifact be created and validated against retained outputs.
5. Resume D-014G only after replay identity is proven.

## Boundaries

No production changes, thresholds/effects/habitat changes, hidden truth in
policy, D-013/AX, formal D-014, formal tag, retries, reseeds, semantic
guessing, or new prospective algorithm. Historical D-014F evidence remains
byte-identical and its claims are not strengthened.

## Evidence

Permanent root:
`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014g1-d014f-artifact-recovery-r1/`

The evidence root is new and isolated from the retained D-014F dossier.


## Closeout

Verdict: `D014G1_D014F_ARTIFACT_UNRECOVERABLE`.

Exact replay was stopped because retained D-014F semantics are incomplete.
No replay artifact was created and the parent D-014G prospective integration
shadow was not resumed. Evidence is frozen under the Atlas root recorded above.
