# CURRENT.md

## Active directive
- ID: D-20260722-umbra-d007-lived-individuality
- Project directive: UMBRA-D-007
- Goal: Implement and validate lived individuality / history-shaped temperament
- Status: in_progress — experiment gates PASS; 100k + 2h soak running; seal pending
- Acceptance: Gates 0-15; QUALIFIED verdict; evidence hashed; Mimir closed; clean worktree
- Touched files: umbra_core/individuality/, experiments/d007/, tests/test_d007.py, docs/evidence/d007/, umbra_core/{runtime,arbitration,events,embodiment}.py, .agent/*
- Next action: await soak; run_seal; commit; close Mimir

## Repo facts needed now
- Starting commit: 79924c7
- Mimir task: 4bcd3653644446979291482242536ddc
- Experiment gates 1-9 style summary: all_pass true
- Deviation: `rng_only_matched_similarity_max` set to 0.55 after C3 diagnostic calibration (before seal)
- Soak: real-time hz=2.0 (tight-loop soak aborted as invalid CPU evidence)

## Last validation
- Command: pytest tests/ (310 passed); pytest tests/test_d007.py (52 passed); run_experiment all_pass
- Result: pending performance soak

## Open blockers
- 2h soak in progress
