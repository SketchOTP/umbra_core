# Regression Results

- `tests/test_d013a_energy_focus.py`: PASS after correction; RED before correction.
- Relevant D-012 process-boundary tests: 3 PASS.
- D-009 evidence validator: PASS (`14` files, `3300` raw rows).
- D-010 evidence validator: PASS (`1900` raw rows).
- Full suite: `692 passed, 2 skipped, 1 failed`.

The one full-suite failure is the pre-existing D-010 runtime-tick inventory/classification test, reporting stale inventory entries and unclassified runtime tick sites. It is unrelated to the arbitration-only change and was not modified under this directive.
