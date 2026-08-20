# AXH Harness Design

AXH separates operational execution identity from scientific logical branch
identity. Every synthetic branch is keyed by a canonical protocol fingerprint,
target/start/depth/parent/action/state/RNG/remaining-depth tuple. PID, worker,
submission order, completion order, time, and UUIDs are excluded.

SQLite is the durable source of operational state. Result payloads are written
to a temporary file, atomically published, hashed, and then attached to a
transaction that marks the branch `COMPLETE`. The summary is derived only from
ledger rows and validated result payloads.

The frontier is outcome-dependent, so parent completion and child insertion are
one transaction. A completed parent remains `expanded=0` until the child set is
durably inserted. Confirmation rows are independently durable and associated
with their source branch.

All synthetic fault cases recover `RUNNING` rows to `PENDING`; conflicting
duplicate result hashes fail closed.
