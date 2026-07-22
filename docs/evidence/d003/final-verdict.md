# UMBRA-D-003 Final Verdict

**Verdict:** `UMBRA_D003_PREDICTIVE_WORLD_MODEL_QUALIFIED`

**Starting commit:** `4a20992ea8a974ce8853e288abb6dc5dfb34b157`
**Ending commit:** `(pending seal commit)`
**Date:** 2026-07-22
**Mimir project:** `7777645d52a91b49`
**Mimir task:** `87f671a62c994e79b36e29fe5c3a00cf`

## Gates

| Gate | Result |
|------|--------|
| 0 Prior seals | PASS |
| 1 Predictive learning | PASS (C0 beats C1/C2/C8) |
| 2 Affordance learning | PASS |
| 3 Object persistence | PASS |
| 4 Contradiction revision | PASS (C4 worse) |
| 5 Generalization | PASS |
| 6 Planning value | PASS |
| 7 Self/world separation | PASS |
| 8 Governance | PASS |
| 9 Persistence/replay | PASS (100 restarts) |
| 10 Regulation | PASS (≥95% energy recovery) |
| 11 Boundedness/performance | PASS (RSS p95 39.04, slope 0.189, CPU 0.325%) |
| 12 Scope and seal | PASS (124 tests, 0 skips) |

## Performance (RUNTIME_READY VmRSS)

| Metric | Result | Threshold |
|--------|--------|-----------|
| duration | 7200.42 s | ≥ 7200 |
| CPU mean | 0.325% | ≤ 5% |
| RSS p95 | 39.04 MiB | ≤ 120 |
| RSS slope | 0.189 MiB/h | ≤ 1.0 |
| counts bounded | true | true |

## D-004

**AUTHORIZED: YES** under `UMBRA_D003_PREDICTIVE_WORLD_MODEL_QUALIFIED`.

## Scientific claim authorized

Bounded organism learns persistent entity estimates, action-conditioned transition models, and affordances from uncertain observations and verified outcomes; supports contradiction revision and bounded planning without LLM or world-truth access.

## Claims not authorized

general intelligence; complete world understanding; consciousness; personality; emotion; relationship; complete companion
