# D-013S regression closeout

Final post-run results:

- D-013R/D-013F/D-013G/D-013H/D-013H-R1/D-013J/D-013M/D-013P/D-013P-R1/D-013A focused boundary: `74 passed`
- D-012 short-path process suite: `35 passed`
- D-009 evidence validator: `PASS` (`14` files, `3300` raw rows)
- D-010 evidence validator: `PASS` (`1900` raw rows)
- governance validator: `PASS` (ADOPTED; `19` required files and `10` Cursor rules)
- full suite: `766 passed, 1 failed, 2 skipped`

The single full-suite failure is the unchanged known D-010 runtime-tick
inventory failure in `tests/test_d010.py::test_all_production_runtime_tick_uses_are_classified`.
No D-013S production or harness change was made.
