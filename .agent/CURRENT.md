# CURRENT.md

## Active directive
- ID: D-20260722-umbra-d005-episodic-consolidation
- Project directive: UMBRA-D-005
- Goal: Selective episodic memory and offline consolidation
- Status: done — UMBRA_D005_MEMORY_CONSOLIDATION_QUALIFIED
- Acceptance: Gates 0–12 met; 178 tests; soak slope 0.449; D-006 authorized
- Touched files: umbra_core/memory/, umbra_core/{runtime,events,embodiment}.py, tests/test_d005.py, experiments/d005/, docs/evidence/d005/, .agent/*
- Next action: D-006 when opened

## Repo facts needed now
- Starting commit: 26235fe80ad9db6268aa9a24fca83678eb431f93
- Ending commit: (set after seal commit)
- Mimir project: 7777645d52a91b49
- Mimir task: bfab230a72a245669aeab9010f949e17
- D-006 AUTHORIZED: YES

## Last validation
- Command: pytest tests/; 2h RUNTIME_READY VmRSS soak; experiments C0–C9×H0–H9 curated
- Result: 178 passed 0 skipped; slope 0.449; gate_performance_pass=true; experiment gates 1–7 true

## Open blockers
- none for D-005
