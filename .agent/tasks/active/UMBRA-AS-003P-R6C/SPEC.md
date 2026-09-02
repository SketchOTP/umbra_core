# R6C scope lock

R6C adds `route_experience_support` and `affordance_support` to a new
`AS003P_PLANNING_EVIDENCE_FRAME_V2` representation. Both are immutable,
source-fingerprinted, shadow-only evidence. Successful V2 route experiences
project as `MAY` historical witnesses; failures remain separate history and
cannot imply future impossibility. V1 records remain historical and do not gain
invented control steps. INSPECT requires a policy-visible instance plus a
matching learned ACTIVE affordance; fixed authored priors are excluded.

The existing V1 fields and modal consumers are unchanged. No runtime action
selection, planner, L2 relation, route-learning lifecycle, owner state, or
Habitat truth is modified.
