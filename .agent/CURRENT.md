# CURRENT.md

## Active directive
- ID: D-20260721-umbra-d003-predictive-world-model
- Project directive: UMBRA-D-003
- Goal: Bounded persistent predictive world model — entities, transitions, affordances, revision, planning
- Status: done — UMBRA_D003_PREDICTIVE_WORLD_MODEL_QUALIFIED
- Acceptance: Gates 0–12 met; 124 tests; soak slope 0.189; D-004 authorized
- Touched files: umbra_core/world_model/, umbra_core/{runtime,embodiment,events,arbitration,governance,perception}.py, tests/test_d003.py, experiments/d003/, docs/evidence/d003/, .agent/*
- Next action: D-004 when opened

## Repo facts needed now
- Starting commit: 4a20992ea8a974ce8853e288abb6dc5dfb34b157
- Ending commit: (seal pending)
- Mimir project: 7777645d52a91b49
- Mimir task: 87f671a62c994e79b36e29fe5c3a00cf
- D-004 AUTHORIZED: YES

## Last validation
- Command: pytest tests/; 2h RUNTIME_READY VmRSS soak; experiments C0–C8×I0–I10
- Result: 124 passed 0 skipped; slope 0.189; gate_performance_pass=true; experiment gates 1–6 true

## Open blockers
- none for D-003
