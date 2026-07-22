# UMBRA-D-006 Interim Verdict (Task 12 — experiment evidence)

**Verdict:** `UMBRA_D006_EXPERIMENT_GATES_1_9_PASS`

**Scope:** Experiment harness + evidence generation. Gates 1-9 asserted numerically
against the frozen `experiments/d006/thresholds.json`. Gate 12 (performance soak) is
deferred to Task 13; gates 10/11 (prior seals, birth/snapshot replay) are covered by
`tests/test_d006.py`. This is NOT the final directive qualification.

**Ending commit:** `6cc0a951af110155baa869457bf9aebc295f3a9a`
**Date:** 2026-07-22
**Mimir project:** `7777645d52a91b49`

## Experiment gates (frozen thresholds)

| Gate | Result |
|------|--------|
| 1 Contingency beats frequency/timing | PASS |
| 2 History separation (pooled/no-memory worse) | PASS |
| 3 Recognition: swap detected, ambiguity kept unknown | PASS |
| 4 Reliability revision + single-anomaly preservation | PASS |
| 5 Social satiation limits bids | PASS |
| 6 Absence: no bids, no punishment, viability held | PASS |
| 7 Developmental routine (scripted C8 disqualified) | PASS |
| 8 Relationship state has episode provenance | PASS |
| 9 Relationship memory never grants authority; C3 isolated | PASS |

## Key measures

- delta_C0 (H0-H1 reliability) = 0.312 (min 0.15)
- history_effect = 0.518; separation C0/C2/C4 = 0.595/0.000/0.217
- single-failure preserved = True; viability_frac = 1.0
- replay determinism = {'identity_equal': True, 'social_accepted_equal': True, 'tick_equal': True}; C3 no-leak = True

## Run

- gate-critical paired seeds: 100
- rows: 1875 across cells ['C0_H0', 'C0_H1', 'C0_H10', 'C0_H2', 'C0_H3', 'C0_H4', 'C0_H5', 'C0_H6', 'C0_H7', 'C0_H8', 'C0_H9', 'C1_H0', 'C1_H1', 'C2_H0', 'C2_H1', 'C3_H0', 'C4_H0', 'C4_H5', 'C5_H0', 'C6_H0', 'C7_H0', 'C8_H10', 'C9_H0', 'C9_H1']
- wall-clock: 11.7 s (8 workers)

## Tests

- `pytest tests/test_d006.py`: 77 passed, 1 skipped in 3.20s
- Gate 12 soak remains skipped by design until Task 13 supplies performance evidence.

## Deferred

- Gate 12 performance soak (RSS/CPU bounds) → Task 13 → `docs/evidence/d006/performance-results.json`
- Final `UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED` requires Task 13 + zero-skip sealed suite.
