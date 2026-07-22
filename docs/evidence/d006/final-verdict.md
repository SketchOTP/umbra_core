# UMBRA-D-006 Final Verdict

**Verdict:** `UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED`

**Ending commit:** `PENDING_SEAL_COMMIT`
**Date:** 2026-07-22
**Mimir project:** `7777645d52a91b49`

## Gates

| Gate | Result |
|------|--------|
| 0 Prior seals (d001/d002p/d003/d004/d005) | PASS |
| 1 Contingency beats frequency/timing | PASS |
| 2 History separation (pooled/no-memory worse) | PASS |
| 3 Recognition: swap detected, ambiguity kept unknown (synthetic + organism real path) | PASS |
| 4 Reliability revision + single-anomaly preservation | PASS |
| 5 Social satiation limits bids | PASS |
| 6 Absence: no bids, no punishment, viability held | PASS |
| 7 Developmental routine (scripted C8 disqualified) | PASS |
| 8 Relationship state has episode provenance | PASS |
| 9 Relationship memory never grants authority; C3 isolated | PASS |
| 10 Prior regressions | PASS |
| 11 Birth/snapshot replay | PASS |
| 12 Performance (100k + 2h soak) | PASS |
| 13 Scope + zero-skip sealed suite | PASS |

## Performance (RUNTIME_READY VmRSS)

| Metric | Result | Threshold |
|--------|--------|-----------|
| duration | 7200.305155754089 s | >= 7200 |
| CPU mean | 0.003475781750305408 frac | <= 0.05 |
| RSS p95 | 40.54296875 MiB | <= 180 |
| RSS slope | 0.22394947490691813 MiB/h | <= 1.0 |
| counts bounded | True | true |
| 100k restart continuity | True | true |

## Experiment

- gate-critical paired seeds: 100
- rows: 1875 across 24 condition x history cells
- delta_C0 (H0-H1 reliability) = 0.312 (min 0.15)
- history_effect = 0.518; separation C0/C2/C4 = 0.595/0.000/0.217
- Gate 3 organism real-path (20 seeds): H8 distinct+swap = 1.0, H8 false-merge = 0.0, H9 ambiguous-not-split = 1.0

## Tests

- `pytest tests/ -q`: 258 passed in 34.40s
- skipped: 0 (final sealed suite requires zero skips)

## UMBRA-D-007

**AUTHORIZED under UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED**

## Scientific claim authorized

Bounded partner recognition, contingency detection from timing, reliability revision, social satiation, absence-robust autonomy, and developmental social routines built on D-005 procedural memory — without an LLM controller, scripted personality, affection meter, or authority grants from relationship memory.

## Claims not authorized

personality; scripted emotion; LLM control; consciousness; general intelligence; complete companion
