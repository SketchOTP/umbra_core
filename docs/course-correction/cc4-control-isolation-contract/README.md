# UMBRA-CC-004 Control / Ablation Isolation Contract

This dossier is `RESEARCH_ONLY`, `NON_QUALIFYING`, and `NOT_FORMAL_EVIDENCE`.
It validates the existing qualified D-009 Gate 5 comparison `g5_c8_fail`:
experimental C0 versus control/ablation C8, both S10/H0 with paired seed 7.

The frozen comparison is `1 - habitat_continuity_l2`, with C0 as A, C8 as B,
`higher_is_better_for_a=true`, threshold 0.0, and material gap minimum 0.02.
The harness proves separate writable databases, explicit roles and execution
IDs, paired-seed semantics without shared mutable state, exact reference/shadow
pair equivalence, true forward/reverse order independence, and 22/22
fail-closed contamination faults with zero silent failures.

The production birth identity is deterministically derived from the shared
paired seed, so C0 and C8 can have the same immutable agent-id and commitment
value. Their identity records remain separate rows in separate databases;
subject IDs, execution IDs, paths, and writable database ownership are distinct.
