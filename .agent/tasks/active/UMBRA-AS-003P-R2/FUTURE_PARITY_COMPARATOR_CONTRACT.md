# AS003PR2 Future Parity Comparator Contract

Any future observer comparator must be frozen before execution and satisfy all
of the following.

- Purely administrative identity renaming is equality-preserving.
- Genuine identity/alias relationships remain comparison-sensitive.
- Dictionary insertion and lexical key order are ignored where owner semantics
  define a map or set, and preserved where order is meaningful.
- Sequence order is preserved for event streams, logs, predictions, errors,
  and other ordered histories.
- Generated identities and every excluded derivative hash are declared by
  owner/source contract rather than a generic name heuristic.
- Primary semantic fields are compared exactly; numerical precision is not
  weakened after observing a mismatch.
- Derivative hashes are reported separately from the source values they hash.
- Owner-specific comparable projections may supplement but never silently
  replace complete field-level comparison.
- Relationship-bearing UUID graphs use bijective, relation-preserving
  canonicalization rather than first-occurrence tokens assigned after raw-key
  sorting.
- The comparator is deterministic, restart-reproducible, and covered by
  positive identity-renaming, negative semantic-value, negative relationship,
  nested-map, and ordering tests.
- Comparator output reports exact differences, semantic differences,
  administrative differences, and derivative differences independently.

The AS-003P-R1 frozen comparator does not satisfy this contract because UUID
dictionary keys remain raw and raw UUID lexical order controls token
assignment.

This contract authorizes no fresh pair. Any later paired execution requires a
new Architect directive and a comparator locked before that execution.
