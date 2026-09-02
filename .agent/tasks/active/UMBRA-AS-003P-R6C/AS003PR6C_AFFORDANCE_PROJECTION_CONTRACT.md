# R6C affordance projection contract

The source snapshot contains bounded WorldModel `AffordanceBelief` records and
the `fixed_authored` configuration bit. An INSPECT evidence row is `MAY` only
when a policy-visible opportunity instance, matching entity kind, learned
`action=inspect`, and `status=ACTIVE` all exist. Fixed authored priors,
missing/ambiguous instances, CANDIDATE, WEAKENED, and SUPERSEDED beliefs are
`UNKNOWN`. No confidence threshold and no Habitat truth are used. The frame
retains affordance support fields as immutable evidence and adds no action
authority.
