# Task 13 Gate 8 Remediation Report

**Agent directive:** `D-20260724-0530-task13-gate8-remediation`  
**Project directive:** UMBRA-D-009  
**Parent Mimir:** `06b5b59709864e11bddb8c1da56dd66e` (stays OPEN)  
**Sub-task Mimir:** `2cce845323eb4746a4e660dc696de46e`  
**Freeze commit:** `4e6c769f916fb7e8d0ca9ce42ddd0462c8654f3b`  
**Base HEAD:** `0d5cffa0a8ca0415f5c4ffe77f0f9a106df8df3a`  
**Outcome:** `UMBRA_D009_TASK13_GATES_1_12_PASS` (not QUALIFIED; Gate 13 deferred Task 14)

## Root cause

Gate 8 `revision_adaptation` failed honestly at **0.08 < 0.10** when evidence was generated with `D009_TICK_CAP=240`. S16 is preregistered at **1800 ticks** (`scenario-suite.json`); truncating to 240 ticks cuts the post-reversal learning window so `_revision_score_s16` / integrated world-model revision rarely reaches threshold.

**Approach ladder step 1** (full preregistered tick budget, no score fallbacks) was sufficient:

| Run | S16 mean `revision_adaptation` | Gate 8 |
|-----|-------------------------------|--------|
| `D009_TICK_CAP=240`, 100 seeds | 0.08 | FAIL |
| No tick cap (S16=1800), 100 seeds | 1.00 | PASS |

No harness or kernel code changes were required.

## Commits

| SHA | Summary |
|-----|---------|
| *(this commit)* | Regenerate D-009 Task 13 evidence at full preregistered tick budgets; Gate 8 PASS |

No code/harness commit — remediation was operational (remove `D009_TICK_CAP` deviation).

## Gates (1–12) at 100 paired seeds

| Gate | Pass |
|------|------|
| 0 regression | ✅ |
| 1 habitat authority | ✅ |
| 2 manipulation | ✅ |
| 3 environmental learning | ✅ |
| 4 autonomy | ✅ |
| 5 persistence | ✅ |
| 6 routines | ✅ |
| 7 individuality | ✅ |
| 8 revision | ✅ (mean 1.00 ≥ 0.10) |
| 9 profile migration | ✅ |
| 10 governance | ✅ |
| 11 replay | ✅ |
| 12 boundedness | ✅ |

Gate 13 **not run** (Task 14).

## Run parameters

- `D009_SEEDS=100`, `D009_WORKERS=8`, **no `D009_TICK_CAP`**
- Software commit at evidence run: `0d5cffa`
- Wall time: ~29 min (full matrix ~4.98M organism ticks)
- Raw ledger rows: **3300**
- Deviations: **none** (prior `D009_TICK_CAP=240` removed)
- Validator: `OK: Task 13 evidence validator passed`

## Tests

- `PYTHONPATH=. python3 experiments/d009/validate_evidence.py` → **OK**
- `pytest tests/test_d009_task13_harness.py -q` → **4 passed**

## Known issues

- None for Gates 1–12 at full tick budgets.

## Next

- Independent re-review of Task 13 evidence path; Task 14 Gate 13 performance soak/seal before QUALIFIED.
