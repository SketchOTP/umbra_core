# Material evidence semantics

The evaluator retains raw observation provenance, including observation ID,
time, estimated distance, confidence, uncertainty, and the original
observation signature. Novelty is derived separately from policy-visible
recovery state.

For the current CHARGE route, the semantic key distinguishes:

- `RESOURCE_NOT_OBSERVED`
- `RESOURCE_PERCEIVED_OUTSIDE_CHARGE_SELECTION_REGION`
- `RESOURCE_PERCEIVED_INSIDE_CHARGE_SELECTION_REGION`

The existing affordance radius plus its established `0.3` execution margin is
used. No new threshold, coordinate, or organism rule was introduced.
