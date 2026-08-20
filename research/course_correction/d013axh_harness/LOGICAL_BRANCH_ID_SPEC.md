# Logical branch identity

`logical_branch_id = sha256(canonical(protocol_fingerprint, target, start_tick,
prefix_depth, parent_logical_branch_id, candidate_action,
counterfactual_input_state_hash, rng_state_reference_hash,
remaining_forced_depth))`.

The identity is stable across process IDs, worker counts, submission order,
restarts, and clean executions of the same frozen protocol. `execution_id` is
operational metadata and is intentionally excluded.
