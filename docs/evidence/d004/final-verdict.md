# UMBRA-D-004 Final Verdict

**Verdict:** `UMBRA_D004_INTRINSIC_DEVELOPMENT_QUALIFIED`

**Starting commit:** `c80a263cacdf93e3385dba3a2fb162bdf5465a28`
**Ending commit:** `21992cfa88cbb7b5c3a856e390b689a4c2c03b67`
**Date:** 2026-07-22
**Mimir project:** `7777645d52a91b49`
**Mimir task:** `712587cdc875470ea635fb302403df47`

## Gates

| Gate | Result |
|------|--------|
| 0 Prior seals | PASS |
| 1 Learning-progress value | PASS (C0 waste-adjusted + beats C2/C3/C4) |
| 2 Autonomous curriculum | PASS (no authored order in C0) |
| 3 Impossible/noisy tasks | PASS (C7 worse on nonlearnable/distractor) |
| 4 Mastery/satiation | PASS |
| 5 Play value | PASS (C0 > C9) |
| 6 Regression/relearning | PASS (C8 slower) |
| 7 Regulation | PASS (energy recovery 1.0) |
| 8 Governance | PASS |
| 9 Persistence/replay | PASS (100 restarts) |
| 10 Boundedness/performance | PASS (RSS p95 39.45, slope 0.449, CPU 0.408%) |
| 11 Scope and seal | PASS |

## Performance (RUNTIME_READY VmRSS)

| Metric | Result | Threshold |
|--------|--------|-----------|
| duration | 7200.47 s | ≥ 7200 |
| CPU mean | 0.408% | ≤ 5% |
| RSS p95 | 39.45 MiB | ≤ 140 |
| RSS slope | 0.449 MiB/h | ≤ 1.0 |
| counts bounded | true | true |

## Experiment

- seeds: 100 matched
- ticks/trial: 100 (+ recovery probe)
- rows: 2400 (24 condition×intervention pairs)
- conditions C0–C9, interventions I0–I10 covered

## D-005

**AUTHORIZED: YES** under `UMBRA_D004_INTRINSIC_DEVELOPMENT_QUALIFIED`.

## Scientific claim authorized

Bounded organism selects practice goals by learning progress (recent vs prior competence windows), satiates mastered goals, dormancy-filters impossible/noisy tasks, relearns after regression, and engages in safe play that measurably improves competence — without LLM, authored curricula, or authority grants.

## Claims not authorized

personality; emotion; social relationship; consciousness; general intelligence; open-ended development; complete companion
