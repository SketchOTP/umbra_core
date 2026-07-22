# CURRENT.md

## Active directive
- ID: D-20260722-1408-d006-task9-ablations
- Project directive: UMBRA-D-006
- Goal: Task 9 — ablations C0–C9 + C3 isolated controller + C4 reset semantics
- Status: done
- Acceptance: met — condition_to_social_config complete C0–C9; C2 pooled + C9 randomized timing; C3 AffectionController isolated under experiments/; C4 resets hypotheses/contingency/pending/routines at boundaries and on restart; 14 new tests + full suite green
- Touched files: umbra_core/social/engine.py, experiments/d006/affection_controller.py, tests/test_d006.py, .superpowers/sdd/task-9-report.md, .agent/*
- Next action: Task 10 persistence/restart/replay contracts

## Repo facts needed now
- Mimir project: 7777645d52a91b49
- Mimir task: c75bd95c868046b580ec6e27140506db
- C3 returns C0 baseline SocialConfig; affection only via experiments/d006/affection_controller.py
- C4 `reset_for_encounter_boundary()` clears pending + routine_handles in addition to hypotheses/contingency

## Last validation
- Command: pytest -q
- Result: 243 passed

## Open blockers
- mimir_validation_run task-scoped runner unavailable (same precedent as Tasks 4–8)
