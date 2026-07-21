# CURRENT.md

## Active directive
- ID: D-20260721-umbra-d002v-seal-validation
- Project directive: UMBRA-D-002V
- Goal: Validate D-002 RSS via current VmRSS; classify event authority; prove replay
- Status: done — UMBRA_D002V_PERFORMANCE_FAIL
- Acceptance: Gate1 failed (slope 1.052 > 1.0); Gates 0/2/3 passed; D-003 blocked
- Touched files: docs/evidence/d002v/, experiments/d002v/, umbra_core/{util,events,runtime}.py, tests/test_d002v.py, .agent/*
- Next action: address Gate1 (new preregistered method or true steady-state RSS) before D-003

## Repo facts needed now
- Verdict: UMBRA_D002V_PERFORMANCE_FAIL
- D-002 functional QUALIFIED remains provisional pending a passing D-002V
- D-003 AUTHORIZED: NO
- Starting commit: a60b9258135867fed63e58109243043162142c3e
- Ending commit: d976fd59c6b737c2db98f2829da780b28cab906e
- Mimir task: 74b43bba377d4c4f85245eb62ad26018

## Last validation
- Command: pytest tests/test_d001.py tests/test_d001c_closeout.py tests/test_d002.py tests/test_d002v.py; soak 2h VmRSS
- Result: 84 passed, 1 failed (rss slope); gate1_pass=false

## Open blockers
- Full-window VmRSS OLS slope 1.052 MiB/h exceeds 1.0 MiB/h (frozen method)
