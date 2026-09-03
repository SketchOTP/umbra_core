# UMBRA-AS-003P-R6F-R1 — terminal closeout

## Verdict

`AS003PR6FR1_PROSPECTIVE_COMMON_ROOT_RELATION_NONDISCRIMINATING`

## Execution

- Baseline: `e5af166e86e85a5937d25b579f9256768bbd3d30`
- Harness-repair commit: `c41efc23f3ee84403c3b0b074877e1beb6df44cc`
- Protocol-lock commit: `38c85f0198bb42bdf8499f8abb33fd18f377caac`
- Command: `/home/sketch/cs14n-runtime/bin/python -m experiments.as003pr6fr1.common_root_assay`
- Scenario/seed/max ticks: `S0` / `18482` / `500`
- Organisms/loads/ticks: `1/0/3`
- Retries/reseeds: `0/0`
- Production delta: `0`
- Existing-test semantic delta: `0`

## Evidence

The complete executable preflight passed twice identically. The one assay
acquired `VERIFIED_ROUTE_EXPERIENCE_V2` at route-learning tick `3`, before
qualification root tick `4`, with exact opportunity
`12fcdda7-98db-5758-ffa7-aad805082c6e` and body schema
`b501305d-c6ad-97ea-b9fc-2a6864376af6`. Both `IDLE {}` and
`MOVE {heading_delta:0.0,step:1.0}` were emitted and hard-admissible. The
source-backed root margin was feasible with six required approaches; `IDLE`
was `PRESERVED` and `MOVE` was also `PRESERVED` because
`move_destroys_existing_route_margin=false`. The strict R6E relation was false
with reason `NO_STRICT_KNOWN_OPTION_PRESERVATION`. The static natural-loss
probe remains a separate prerequisite finding and was not promoted to live
candidate causality.

## Integrity

No R6F historical file/evidence, production file, R6E implementation, planning
reader, candidate semantics, or arbitration semantics changed. No R7, planning,
diagnostic, control/shadow, retry, or reseed activity occurred.

Evidence root:
`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r6f-r1-common-root-option/`.
