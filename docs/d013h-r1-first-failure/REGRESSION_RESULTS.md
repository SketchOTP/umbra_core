# Regression results

Focused R1 tests cover evaluator initialization, identity, init exclusion,
worker replacement, duplicate/cross-run rejection, zero-recovery publication,
first-failure ordering, secondary publication failure, no-prior-failure
terminal behavior, pre-database termination, read-only failure identity, and
V1 compatibility.

Final focused R1 coverage: `12 passed`.

Combined D-013H-R1, D-013H, D-013G, D-013F, D-013A, D-012 process, and D-012
coverage: `78 passed` (12 R1 plus the previously governed 66-test set).

D-009 validator: PASS, 3,300 raw rows. D-010 validator: PASS, 1,900 raw
rows. Canonical governance validation and governance matrix tests: PASS.

Full repository suite: `735 passed, 2 skipped, 1 known unchanged D-010
runtime-tick inventory failure`. The failure is the existing
`test_all_production_runtime_tick_uses_are_classified` inventory failure and
was not modified by R1.
