# CURRENT.md

## Active directive
- ID: D-20260724-1620-d010-freeze-invalidate-v5
- Project directive: UMBRA-D-010
- Goal: Freeze invalidate v5 — Task 14 QUALIFIED seal path + Stage B v5
- Status: complete
- Acceptance: met — seal can QUALIFY when earned; perf protocol honest; manifest complete; pytest+contract green; d010-fe-stage-b-v5 frozen; no QUALIFIED claim
- Fix commit: `5911cdd`
- Freeze tip: `3178815` / `d010-fe-stage-b-v5`
- Invalidated: `f13d976` / `d010-fe-stage-b-v4`
- Preserved Task 13d evidence: `c52f311` (must re-run under v5 before QUALIFIED)

## Locked
- Parent Mimir: `9adf61b087ea4fa6a90a1c3bd401a9b3` (OPEN)

## Last validation
- Command: `python -m pytest tests/test_d010.py -q` + `python -m pytest -q` + `run_seal.py --contract-only`
- Result: 126 passed; 643 passed 2 skipped; contract_ok true

## Open blockers
- None for invalidate v5; Gates 1–12 + Gate 13 formal campaigns remain before QUALIFIED
