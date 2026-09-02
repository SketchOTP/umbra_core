# R6A result

## Terminal verdict

`AS003PR6A_ROUTE_DEMAND_LEARNING_PRIMITIVE_REQUIRED`

The exact baseline `dbb95c3176573919d003d90b25f745853bfe803c` reconciled across
local `HEAD`, local `master`, `github/master`, and the canonical Notion R6A
authority. R6A remained source-only.

## Findings

- WorldModel supplies body-relative bounded distance support with provenance,
  but not a traversable route-length upper bound.
- SelfModel supplies APPROACH progress/applied-step/completion intervals from
  verified outcomes, but their semantics are `VERIFIED_OBSERVED_SUPPORT`; they
  are not future guaranteed progress bounds. Body-schema matching is necessary
  but insufficient for transfer.
- The candidate distance/progress quotient is therefore `UNKNOWN_ROUTE_DEMAND`
  for robust L2 scheduling. It may be an observed/MAY projection only when
  geometry and source semantics are explicitly established.
- Non-delayed CHARGE, REST, and INSPECT can be verified in the issue tick, but
  this is capability-specific runtime behavior, not a transferable route or
  service timing guarantee. Future evidence must separate service-step demand
  from completion lag.
- A lawful INSPECT join requires a specific policy-visible instance plus a
  matching ACTIVE affordance belief. Kind-level affordance evidence alone
  cannot invent an instance; Habitat `inspectable` truth remains execution
  authority. The retained R5A frame does not carry affordance beliefs.
- Retained R5A coverage: 500 frames, 1,000 opportunity rows, 498 frames with
  positive APPROACH support, 0 route-demand fields, 0 affordance-bearing
  frames, and 0 nonzero terminal timing rows. This is coverage evidence only.

## Smallest next boundary

Acquire a new verified route-demand evidence fact that is opportunity-specific,
body-schema-bound, provenance-bearing, uncertainty-preserving, and explicit
about route blockage/failure and completion semantics. It must not be a score,
weight, planner, or hidden Habitat truth. No successor was authorized or
started.

## Integrity

Isolated pure source-contract tests passed `10/10` twice. Production delta,
existing-test semantic delta, organism/control/shadow/diagnostic runs, retries,
and reseeds were all `0/0/0/0/0/0`. Authority 3.0, governance, `git diff
--check`, and evidence readback passed. Final evidence manifest SHA-256:
`3685ff9e7ae4bb95200adbb0fb1ddc18bfb1df10c48e2cc252aa15373e2507ba`.

Final GitHub commit and records are included in the pushed R6A closeout commit.
