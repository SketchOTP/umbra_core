# UMBRA-D-002P Final Verdict

**Verdict:** `UMBRA_D002P_PERFORMANCE_REMEDIATION_QUALIFIED`

**Starting commit:** `97e5df2175817b9122f5724aaedd2c320d12510c`  
**Soak / remediation commit:** `13bdce2311b2a9571d2efcf1a6500a91760bb171`  
**Date:** 2026-07-21  
**Mimir project:** `7777645d52a91b49`  
**Mimir task:** `8e2d40832317467c8eee34ab873e6234`

## Gate 0 — Prior result preserved

D-002V remains `UMBRA_D002V_PERFORMANCE_FAIL` (full-window VmRSS OLS 1.052 MiB/h). Not waived. Not redefined.

## Gate 1 — Memory attribution

Documented in `memory-attribution.md` / `memory-profile.json`. Primary growth was startup population + SQLite page residency; late-window retention is bounded (hour2 OLS ≈ 0.19 MiB/h). Remediation: BoundedRing + in-place reuse, snapshot prune (keep=2), drop duplicate metrics list, fixed 6 MiB `runtime_warm` before `RUNTIME_READY`.

## Gate 2 — Behavioral equivalence

`behavior-equivalence.json` pass: prediction, I1 adaptation, I8 external attribution, identity restart.

## Gate 3 — Performance (preregistered RUNTIME_READY method)

| Metric | Result | Threshold |
|---|---|---|
| duration | 7200.08 s | ≥ 7200 |
| measurement start | first `runtime_ready` | — |
| CPU mean | 0.257% | ≤ 5% |
| RSS p95 | 37.60 MiB | ≤ 100 |
| RSS slope | **0.217 MiB/h** | ≤ 1.0 |
| crash-free | yes | yes |

## Gate 4 — Persistence / replay

`replay-results.json` pass: birth resimulation + snapshot replay; collection bounds held (predictions/errors/attributions=256, snapshots=2); ledger + restart identity OK.

## Gate 5 — Tests and seal

`pytest tests/` → 99 passed, 0 failed, 0 skipped.

## D-003

**Authorized:** YES (under `UMBRA_D002P_PERFORMANCE_REMEDIATION_QUALIFIED`)
