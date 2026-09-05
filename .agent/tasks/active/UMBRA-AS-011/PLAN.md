# UMBRA-AS-011

Status: terminal, `AS011_PROTOCOL_FAIL`.

Baseline: `bcd5ff361a22288480dd16cf20e3aad432bda26e`.

Accepted predecessor: `AS010_PROTOCOL_FAIL`.

Scope: downstream boundedness recovery, current full-configuration real-time soak,
and isolated causal ablations. Production semantics, historical evidence, AS-010's
population/lifecycle, and the partial AS-010 100k run remain unchanged.

Phase 0 established zero production delta and retained-evidence insufficiency. The
non-formal terminal snapshot/restart preflight passed after restoring HabitatEngine
before authoritative reads. Protected tests passed `27/27` twice and the scientific
lock was committed. The frozen boundedness command then failed before organism
creation with `NameError: name 'bounded' is not defined` at
`experiments/as011/downstream.py:98`; no retry/reseed followed. Soak and ablation
were not run.
