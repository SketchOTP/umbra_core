# D-010-R1 RSS root-cause diagnosis

**Directive:** UMBRA-D-010-R1 / `D-20260724-1607-d010-r1-rss-remediation`  
**Failed freeze preserved:** `3178815` / `d010-fe-stage-b-v5`  
**Failed verdict preserved:** `UMBRA_D010_PERFORMANCE_FAIL`  
**Harness:** `experiments/d010/run_rss_diagnosis.py` (production-unreachable)

## Round 1 — classified and patched (`bab1fcd`)

```text
A. Unbounded TemporalEngine._committed_advance_ids / observation-plan sets
```

Also attempted snapshot-path `shrink_memory`+`malloc_trim` (revised below).

## Round 1 formal rerun (freeze v6)

- P0 still FAIL at 1.665 MiB/h (OLS ≈ 0.52; Theil–Sen + sustained segments)
- Absolute RSS improved; temporal-specific set owner removed

## Round 2 — residual owners and fix

| Finding | Evidence |
|---------|----------|
| Residual growth is **RssAnon** (not Python objects, not file RSS) | smaps_rollup 900s soak |
| Common-path: temporal_off ≈ baseline trough Δ | 30 min ablations |
| Snapshot-path shrink+trim creates 100s sawtooth → S3 fail | formal soak-P0 vs D-009 WAL-only |
| P0 passes with **WAL-only malloc_trim** (D-009 pattern) | slope 0.597, segs non-sustained |
| P1/P2 fail on expression refill after WAL | P1 1.09 slope; fixed-cadence trim flips to sustained-seg fail |
| **Adaptive** expression trim (trim only if RSS grew ≥0.4 MiB) | P1 PASS 0.625, segs [44.94, 45.17, 45.37] |

### Root-cause package (final)

| Field | Value |
|-------|-------|
| root cause | (1) Unbounded advance-id sets; (2) snapshot-path shrink+trim sawtooth; (3) expression-path RssAnon refill after WAL without adaptive return |
| retaining owner | TemporalEngine sets; glibc arenas; expression frame overwrite churn |
| reproduction | Formal P0/P1/P2 under Stage B; diagnosis harness modes |
| measured contribution | Set fix removed temporal-specific owner; WAL-only restored P0; adaptive expr trim restored P1 |
| affected files | `umbra_core/temporal/engine.py`, `umbra_core/runtime.py`, tests/manifest |
| smallest corrective change | Bound committed-id sets; WAL-only `malloc_trim`; adaptive expression trim on measured RSS growth |
| expected regression risk | Low–moderate — adaptive trim is expression-gated; P0 path unchanged from D-009 WAL policy |

## Artifacts

- Failed freeze `3178815` Task 14 evidence **unchanged**
- Isolation outputs under `docs/evidence/d010/rss-diagnosis/`
