# UMBRA-AS-003P-R6B — Verified Opportunity Route-Demand Learning Primitive

## Baseline and purpose

Start from `3604fa6a4a4e01c764913af55474e7ad9495325f`, after terminal R6A
`AS003PR6A_ROUTE_DEMAND_LEARNING_PRIMITIVE_REQUIRED`. Implement and qualify only
the smallest verified route-experience source primitive required by R6A.

## Contract

- WorldModel owns `VerifiedRouteExperience`; the default is disabled.
- A completed fact is bound to one policy-safe WorldModel opportunity entity and
  one body schema. No cross-opportunity or cross-body transfer is allowed.
- Only attributed `VerifiedOutcome` episodes may create facts. Raw movement count,
  each movement completion lag, terminal completion lag, terminal result, route
  failure, timing, and provenance remain separate fields.
- Resolution is `EXACT`, `AMBIGUOUS`, or `UNAVAILABLE`; no nearest, confidence,
  lexical, authored, Habitat, scalar, or utility selection.
- Incomplete, denied, unverified, ambiguous, interrupted, switched, stale, or
  body-invalid episodes are discarded. Completed evidence persists through
  snapshot/restart and is bounded by a fixed capacity; incomplete episodes are
  ephemeral.
- There are no readers in candidate generation, arbitration, distributed or
  stochastic competition, Governance, Embodiment, recovery authority, modal/L2,
  legacy planning, or action selection.

## Prohibitions

No planner integration, no planning-frame extension, no AS-002/CLOSE-02Z change,
no physiology or candidate semantic change, no Habitat truth, no score/utility/
probability/weight/priority, no long-horizon run, no successor authority.

## Validation boundary

Pure source/object tests must pass before one bounded successful route assay and
one bounded route-failure assay. Protected regressions are run afterward. All
execution evidence is durable and per-command; organism counts remain explicit.
