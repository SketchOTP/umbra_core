# UMBRA-AS-003P-R6E — Known recovery-option preservation relation

## Terminal result

`AS003PR6E_KNOWN_RECOVERY_OPTION_PRESERVATION_RELATION_SUPPORTED`

R6E is a zero-organism, non-authoritative relation study. It does not modify
the preserved R6 `l2_precedes()` relation and does not grant planning or
action-selection authority.

## Evidence boundary

The relation uses one fixed common root option set for both candidates. A known
source-backed option is `PRESERVED` only when at least one support variant is
feasible on every supported candidate branch. It is `DESTROYED` only when every
support variant has a definitively infeasible supported branch. Otherwise it is
`UNKNOWN`; unknown is never treated as loss.

The proposition is only: candidate A preserves a known option that candidate B
destroys, with no converse loss and no asymmetric unknown. It does not claim
that B is unrecoverable, unsafe, suboptimal, or without an unobserved future
route.

## Frozen-matrix result

The immutable R6D matrix contained 1,152 configurations. R6E found:

- 256 ordinary hard-admissible comparisons;
- 192 positive preservation relations;
- 64 route-causal ordinary relations;
- 128 non-route option-loss relations;
- 256 hard-authority-preempted comparisons;
- 640 root-option-empty cases;
- 0 obligation-signature mismatches;
- 0 asymmetric-UNKNOWN blocks in this symbolic matrix;
- 320 `PRESERVED` and 192 `DESTROYED` per-candidate option statuses;
- 96 R6D `COMPLETE_MAY`/`SCHEDULE_UNKNOWN` distinctions, with 32 overlapping
  route-causal R6E relations.

The zero unknown-status count is a property of the finite symbolic matrix, not
a claim that real UMBRA evidence is complete.

## Retained witness probe

The immutable seven-tick R6B-R1 witness remains `MAY /
VERIFIED_OBSERVED_SUPPORT`. Under synthetic development deadlines, it is
`PRESERVED` at deadline 8, `DESTROYED` at deadline 5, and `UNKNOWN` when
applicability is unknown. These are relation probes, not organism observations.

## Validation and scope

The isolated pure suite passed `26/26` twice with identical output. The source-
priority audit passed: semantic duplicate evidence collapses, confidence and
provenance do not alter relation, duration is neutral unless feasibility changes,
and unknown is not loss. Production delta, existing-test semantic delta,
organism/load/tick/control/shadow/diagnostic runs, and retries/reseeds are all
zero. R6D and all prior evidence remain immutable.

## Next step

`UMBRA-AS-003P-R7 — Prospective Known-Option-Preservation Common-Root Shadow
Qualification` is recommendation-only. It was not started automatically.

Evidence root (local/internal provenance):
`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r6e-known-option-preservation-r1/`.
