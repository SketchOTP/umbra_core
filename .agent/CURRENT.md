# CURRENT.md

## Active directive
- ID: D-20260720-umbra-d001c-performance-closeout
- Project directive: UMBRA-D-001C (parent UMBRA-D-001) — closing
- Goal: Seal D-001 QUALIFIED from Run B evidence
- Status: done — Run B passed all gates; 45/45 tests; sealing
- Acceptance: met
- Touched files: docs/evidence/d001/*, experiments/d001/closeout_run_b.py, tests/test_d001c_closeout.py, .agent/*, UMBRA-D-001 directive
- Next action: none for D-001; D-002 authorized when opened

## Repo facts needed now
- Verdict: UMBRA_D001_INVARIANT_COMPANION_CORE_QUALIFIED
- D-002 AUTHORIZED: YES (not started)
- Run B commit: 8d68995d114504e1265eef1941a0b46588b0893e
- Mimir task: a9d8858e78824663ae88103cf735c025

## Last validation
- Command: closeout_run_b.py; pytest tests/test_d001.py tests/test_d001c_closeout.py -q
- Result: gate9_pass=true; 45 passed, 0 skipped

## Open blockers
- None for D-001
