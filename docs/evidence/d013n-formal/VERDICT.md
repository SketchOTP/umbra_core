# UMBRA-D-013N Verdict

`D013N_FORMAL_RUN_INVALID`

The single authorized V2 invocation was issued from the frozen baseline using
`--starting-commit 414e60f`, but the direct script entrypoint failed before
organism startup because its package-relative import had no known parent
package. `run_count` is `1`; `organism_started` is `false`. No retry,
module-entrypoint substitution, code change, harness change, threshold change,
or remediation was performed.

This is not a scientific viability result. The immutable formal tag remains
anchored to `414e60fdf354217ea47afc22485413dc6e010eb9`.
