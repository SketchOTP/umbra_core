# D-010-R1 diagnostic campaign — 2026-07-25 (final patch, uncommitted)

**Patch under test:** bounded advance/observation-id sets + WAL-only `malloc_trim`
(no snapshot-path `shrink_memory`) + adaptive expression trim (every 50 ticks,
only when RSS grew ≥ 0.4 MiB since last expression trim).
**Source base:** `95e43c9` + uncommitted remediation. Diagnostic evidence only —
not qualification evidence. Failed freeze `3178815` untouched.

## Results (S3 protocol, full 3600 s measurement each)

| Mode | Run | Verdict | Robust slope | Segments | Sustained |
|------|-----|---------|--------------|----------|-----------|
| P0 | 2026-07-24 21:10 | PASS | 0.597 | [45.36, 45.55, 45.76] | no |
| P1 | 2026-07-25 05:56 | PASS | 0.625 | [44.94, 45.17, 45.37] | no |
| **P0 reconfirm** | 2026-07-25 10:49 | **FAIL** | **1.199** | [44.98, 45.32, 45.98] | **yes** |
| **P2** | 2026-07-25 11:54 | **PASS** | **0.635** | [53.99, 54.22, 54.41] | no |

Artifacts: `diagnostic-P0-reconfirm-20260725.json/.jsonl`, `diagnostic-P2-20260725.json/.jsonl`
(P1/P0-pass evidence in overwritten `performance-*.json` history is captured in
`.agent/OUTCOMES.md` and Mimir observations).

## Finding

- **P2 blocker resolved:** prior 1.19 → 0.635 under adaptive expression trim.
- **New blocker:** P0 is not reproducibly ≤ 1.0. Two runs of the *identical* P0
  code path (expression disabled — the adaptive trim is not even reachable in P0)
  produced 0.597 PASS then 1.199 FAIL. Run-to-run spread ≈ 0.6 MiB/h around the
  1.0 limit; today's fail also tripped `sustained_segment_growth` with a total
  post-warmup rise of ~2.5 MiB over the hour.
- OLS full-window slopes: 1.817 (P0 fail) vs 1.094 (P2 pass) — both estimator
  and underlying series vary with ambient conditions; the marginal band spans
  the frozen threshold.

## Status per directive gate

```text
P0 + P2 both pass: NOT MET (P0 reconfirm failed)
Stage B v7: NOT created
Patch iteration: STOPPED
UMBRA_D010_PERFORMANCE_FAIL retained
QUALIFIED not authorized
parent Mimir open
failed freeze 3178815 preserved
```

## Open question for operator

The remediation is behaviorally correct (bounded structures verified by tests;
Python heap and object counts flat; growth is glibc RssAnon residency), but the
P0 slope outcome under the frozen S3 estimator is stochastic across identical
runs. Options are operator decisions, not agent patches: repeat-run protocol
evidence, longer measurement, or accepting the fail and re-diagnosing the
residual RssAnon creep (~0.85 MiB/h trough envelope on failing runs).
