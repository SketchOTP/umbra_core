# Equivalence results

Status: `PASS`.

The bounded C0/S0 reference route and shadow-contract route used seed 7 and 40
ticks. All declared deterministic fields matched exactly: definition and seed
fingerprints, tick count, terminal outcome, and the complete declared metric
subset. The run was isolated under a CC-2-owned temporary directory and marked
`RESEARCH_ONLY`, `NON_QUALIFYING`, `NOT_FORMAL_EVIDENCE`.

The initial run exposed one real boundary distinction: existing D-009 applies a
C0/S0 baseline collector convention for `governed_alignments`. The shadow route
now represents that rule explicitly. No arbitrary tolerance was introduced.
