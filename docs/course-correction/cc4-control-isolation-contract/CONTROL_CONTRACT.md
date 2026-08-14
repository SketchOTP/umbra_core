# Control Contract

The pair is immutable: C0 is experimental, C8 is control/ablation, both use
S10/H0 and the same paired seed. Only `condition` differs. Every subject has a
subject ID, execution ID, role, condition, scenario, history, seed, database
path, and definition fingerprint. Role is explicit and never inferred from
execution order. Unknown, duplicate, swapped, missing, or extra roles fail
closed.
