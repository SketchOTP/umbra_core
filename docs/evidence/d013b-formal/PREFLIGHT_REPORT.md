# UMBRA-D-013B Preflight Report

Verdict: `D013B_PREFLIGHT_FAIL`

Formal P0 execution was not started. No organism execution, retry, remediation, or formal evidence generation occurred.

## Baseline

- HEAD: `d3a8b9a7cfb2222faab4b994b778e4efea43b16c`
- Branch: `master`
- Remote master: `d3a8b9a7cfb2222faab4b994b778e4efea43b16c`
- Formal tag: `umbra-d013-formal-baseline-d3a8b9a`
- Tag target: `d3a8b9a7cfb2222faab4b994b778e4efea43b16c`

## Gate results

- Baseline and tag: PASS
- D-012B1/B2 evidence hashes: PASS; unchanged
- D-009 validator: PASS (`14` files, `3300` raw rows)
- D-010 validator: PASS (`1900` raw rows)
- D-013A focused regression: PASS
- D-012 process/supervision regression: FAIL (`25 passed, 1 failed`)
- Stale formal process/worker/lock/socket check: PASS

The failed test was `test_signal_during_ordinary_ticking_recovers_identity[False]`. The replacement worker launch failed with `ORGANISM_START_FAILED: exit:1` after ordinary worker termination. Because D-013B requires every preflight gate to pass, formal P0 was not launched.

## Integrity

- D-012B1 modified: false
- D-012B2 modified: false
- Historical verdicts modified: false
- Thresholds modified: false
- Production code modified after formal tag: false
- Formal run count: `0`
- Retries performed: `0`
