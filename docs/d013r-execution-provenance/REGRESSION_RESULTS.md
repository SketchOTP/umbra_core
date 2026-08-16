# D-013R validation

- focused D-013R tests: `8 passed`
- D-013A/F/G/H/H-R1/J/M/P/P-R1 family: `74 passed`
- D-012 short-path process suite: `35 passed` using `/mnt/storage1tb/uD13R`
- D-009 validator: `PASS` (`14` files, `3300` raw rows)
- D-010 validator: `PASS` (`1900` raw rows)
- governance validator: `PASS` (ADOPTED)
- path-safe full suite: `766 passed, 2 skipped, 1 unchanged D-010 inventory failure`

The full suite was run with `/tmp` because frozen D-008/D-010 disposable-DB
guards intentionally reject secondary-storage pytest paths. The D-012 process
suite passed independently on the short governed secondary path after `/tmp`
quota pressure produced environment-only failures.
