# D-013P Regression Results

- Focused D-013P, D-013M, D-013A, D-013F, D-013G, D-013H, D-013H-R1, and D-013J tests: 55 passed.
- D-012 process suite with short AF_UNIX-safe basetemp /tmp/u-d013p-d012: 35 passed.
- D-009 validator: PASS, 14 files and 3,300 raw rows.
- D-010 validator: PASS, 1,900 raw rows.
- Governance validator: PASS in ADOPTED mode.
- Path-safe full suite with /tmp/u-d013p-full-final: 747 passed, 2 skipped, 1 failed.
- The sole full-suite failure is the unchanged D-010 runtime-tick inventory test; no new D-013P-related failure remained after preserving the D-008 memory regression.
- The two Tk import warnings are environmental and unchanged.

No formal P0, formal tag, D-013O evidence, historical evidence, threshold, contract, or verdict was modified.
