# Deduplication durability

Logical branch identity is unique in SQLite. Exact state identity is included
in the identity payload; no approximate matching or numerical clustering is
used. A duplicate with the same canonical result hash is operationally
idempotent. A duplicate with a different hash raises
`NONDETERMINISTIC_DUPLICATE_RESULT` and cannot be silently selected.
