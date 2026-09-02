# UMBRA-AS-003P-R6B-R1 result

## Terminal verdict

`AS003PR6BR1_VERIFIED_ROUTE_CONTROL_LEARNING_QUALIFIED`

This is a fresh bounded repair generation from `e610a36f4ca07cf451da53c9f7dac9d35a037a0e`, not a rewrite or retry of the permanently failed R6B generation.

## Scope and implementation

The repaired WorldModel route-evidence seam admits only exact opportunity- and body-schema-bound verified outcomes. Same-target `ORIENT` preserves an active route episode and is recorded as a non-translational `VerifiedRouteControlStep`; successful translational movement count remains limited to `APPROACH`. Ordered steps retain capability, issue/completion ticks, observed completion lag, success, and VerifiedOutcome provenance. Unbound/ambiguous/switched/body-mismatched/unverified/unrelated actions fail closed. Issued `IDLE` is a route interruption. Existing V1 records remain readable without invented control steps; new records use V2.

Route evidence remains default-off and has no reader in candidate generation, arbitration, distributed or stochastic competition, Governance, Embodiment, recovery authority, hypothetical/modal planning, or action selection.

## Frozen assay

Freeze commit: `caab6c08110f9e05f655360b5d5304c9aec7f767`.

The exact frozen command was `/home/sketch/cs14n-runtime/bin/python -m experiments.as003pr6br1.route_learning_assay` from `/home/sketch/Projects/umbra-close02x-work`, using seed `6103`, scenario `S0`, max `8` ticks, one nominal and one failure leg, and retries/reseeds `0/0`.

Q1 nominal PASS: one completed verified experience for opportunity `2b311f40-2dcf-394b-ecd0-9de8088ceb67` under body schema `802b456c-678c-aee1-6a92-a0e4e1f87afe`; ordered route-control capabilities were `ORIENT, CHARGE, ORIENT, CHARGE, APPROACH, ORIENT, CHARGE`; translational movement count `1`; ORIENT count `3`; terminal `CHARGE` verified; all seven outcome references retained.

Q2 failure PASS: same exact opportunity/body binding; verified `movement_slip`; terminal result false; no false successful experience.

Execution accounting: organisms `2`, ticks `14` (`8` nominal + `6` failure), retries `0`, reseeds `0`. These are the bounded lifecycle assay counts; the pre-freeze pure tests used isolated value/WorldModel fixtures and did not create or tick organisms.

## Validation

- Pure protected route suite: `41 passed` on repeated pre-freeze runs and post-freeze protected regression.
- Assay equivalence: PASS; fixture, selector, configuration, retry, and reseed semantics match R6B, with only authorized namespace/evidence metadata and route-control capture differences.
- Policy isolation, default-off behavior, bounded capacity, V1 migration, timing/provenance, exact identity binding, and `git diff --check`: PASS.
- Authority 3.0: PASS. Governance: PASS.
- Production changes: limited to `umbra_core/world_model/route_evidence.py` and its exports. No candidate/arbitration/planning/AS-002/CLOSE-02Z change.

Evidence root: `/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r6b-r1-route-control-continuity-r1/`.

Key durable artifacts include the route-continuity contract, assay-equivalence audit, pre-execution integrity record, frozen command stdout/stderr/record, operational assay result/validation, pure-run records, and protected-regression record. The final evidence manifest is published at closeout.

## Boundary and recommendation

This qualifies verified route-control learning only. It does not grant planning or action-selection authority, does not reinterpret R6B, and does not qualify integrated long-horizon viability. Recommendation only: `UMBRA-AS-003P-R6C — Route/Affordance Planning Evidence Frame Extension Candidate`. No successor was started.
