# Audit chain

Events hash-link (`prev_hash`) and Ed25519-sign; bind policy_version, capability_version, body_binding, lifecycle_sequence, causal parents.

Attacks detected in independent harness: mutation, deletion, reorder, replay, revoked signer, stale backup, duplicate migration.

Hash linkage alone is insufficient — version bindings required.
