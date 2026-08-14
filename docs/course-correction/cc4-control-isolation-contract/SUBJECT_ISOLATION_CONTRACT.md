# Subject Isolation Contract

C0 and C8 use separate disposable writable directories and SQLite files,
separate Store connections, separate identity rows, separate snapshot and
event-ledger namespaces, and separate in-memory organism/habitat instances.
Execution IDs, subject IDs, and roles are distinct. The deterministic agent
ID/identity commitment collision caused by the intentionally shared seed is an
immutable derivation, not shared storage or mutable state, and is recorded as
such rather than silently treated as unique.
