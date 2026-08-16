# D-013L post-run regressions

- D-012 short-path process suite: `35 passed` using `--basetemp=/tmp/u`.
- D-012 post-run process suite: `35 passed` using `--basetemp=/tmp/u-post`.
- D-013A focused regression: `1 passed`.
- D-009 evidence validator: PASS (`14` files, `3300` raw rows).
- D-010 evidence validator: PASS (`1900` raw rows).
- Governance validator: PASS (`ADOPTED`).
- Full suite: `740 passed, 1 failed, 2 skipped`; the failure is the existing
  D-010 runtime-tick inventory test.

No production, test, experiment, threshold, or historical-evidence files were
modified by the formal run or post-run validation.
