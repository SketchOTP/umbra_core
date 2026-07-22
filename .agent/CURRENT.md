# CURRENT.md

## Active directive
- ID: D-20260722-1256-d006-task5-pending-atomic
- Project directive: UMBRA-D-006
- Goal: Pending interaction lifecycle + contingency classification precedence + atomic social outcome SQLite commit (crash-safe, restart-safe, no double-evidence)
- Status: done
- Acceptance: met — 9 brief tests pass; single-transaction outcome commit; crash between stages leaves no partial durable/in-memory state; denied/expired/failed + non-evidence classes build no reliability; double-evidence blocked; missing authoritative pending event fails closed
- Touched files: umbra_core/social/{engine,__init__}.py, umbra_core/persistence.py, umbra_core/memory/engine.py, umbra_core/events.py, tests/test_d006.py, .superpowers/sdd/task-5-report.md, .agent/*
- Next action: Task 6 — runtime propose/observe wiring + routine promotion

## Repo facts needed now
- Mimir project: 7777645d52a91b49
- Mimir task: 8bd7e271d3534997b6e04f7ca5e90fd9
- Classification precedence: EXTERNAL→AMBIGUOUS→CONTINGENT[1,8]→DELAYED[9,24]→COINCIDENTAL→NONE(timeout 32)
- atomic commit: Store.atomic_social_outcome (BEGIN IMMEDIATE, crash_after_stage, on_commit post-COMMIT)

## Last validation
- Command: pytest tests/test_d006.py -q ; pytest d001..d006 -q
- Result: 30 passed ; 208 passed

## Open blockers
- mimir_validation_run "validation requires an active observed task" (allowlist has 'pytest -q' but task-scoped runner rejects) — validated locally; recorded honestly (same precedent as Task 4)
