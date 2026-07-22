# CURRENT.md

## Active directive
- ID: D-20260722-1320-d006-task5-review-fixes
- Project directive: UMBRA-D-006
- Goal: Fix Task 5 review Finding 1 (create_pending/resume_pending mutate memory before durable write/bound check) and Finding 2 (social_pending_interrupted never produced)
- Status: done
- Acceptance: met — create_pending/resume_pending check bound and write the durable event before any in-memory mutation; interrupt_pending(pid,reason) added and wired via recognize() CONTESTED-transition and resume_pending corrupted-timing; 3 new regression tests pass; full suite green (211)
- Touched files: umbra_core/social/engine.py, tests/test_d006.py, .superpowers/sdd/task-5-report.md, .agent/*
- Next action: Task 6 — runtime propose/observe wiring + routine promotion

## Repo facts needed now
- Mimir project: 7777645d52a91b49
- Mimir task: 1c8964fa5cb44488a4cbe5effd571a18
- Classification precedence: EXTERNAL→AMBIGUOUS→CONTINGENT[1,8]→DELAYED[9,24]→COINCIDENTAL→NONE(timeout 32)
- atomic commit: Store.atomic_social_outcome (BEGIN IMMEDIATE, crash_after_stage, on_commit post-COMMIT)
- Pending capacity gate: _ensure_pending_capacity() raises before any mutation once open (PENDING) count == MAX_PENDING_INTERACTIONS (8)
- Interrupt path: interrupt_pending(pid, reason, store, tick) — durable write before status mutation; called from recognize() (reason="recognition_contested") and resume_pending (reason="corrupted_timing_state")

## Last validation
- Command: pytest tests/test_d006.py -v ; pytest tests/ -q
- Result: 33 passed ; 211 passed

## Open blockers
- mimir_validation_run "validation requires an active observed task" (allowlist has 'pytest -q' but task-scoped runner rejects) — validated locally; recorded honestly (same precedent as Task 4/5)
