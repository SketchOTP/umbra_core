# D-013R correction rationale

This is implementation alignment with the frozen V2 semantics, not a contract
change. The existing `normalize_trace_row()` already preferred
`executed_capability`; `classify_attempt()` was the inconsistent downstream
stage. V2 contract version and fingerprint remain unchanged.

The correction:

- derives one canonical `attempt_capability` from authoritative execution,
  verified outcome, and governance capability;
- treats `selected_candidate` as diagnostic-only when authoritative capability
  data exists;
- fails closed on true execution/verified/governance disagreement;
- derives corrective action, recovery blocking, and repeated-denial comparison
  from the canonical action; and
- records the canonical action and provenance reasons in evaluator traces.

No `not_at_rest` expansion was added to CHARGE denial semantics. REST remains
REST.
