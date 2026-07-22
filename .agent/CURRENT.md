# CURRENT.md

## Active directive
- ID: D-20260722-1412-d006-task10-persistence-replay
- Project directive: UMBRA-D-006
- Goal: Task 10 — persistence, restart, replay contracts (Gate 11 + event sourcing)
- Status: done
- Acceptance: met — SocialEngine.accepted_state() added + wired into resimulate(); routine_handles bounded across full hypothesis lifetime (retirement interrupts + MAX_ROUTINE_HANDLES=32 FIFO prune); 6 brief tests (restart/replay/bounded-counts/prior-seals/prior-regressions/no-deferred-modules); full suite green
- Touched files: umbra_core/social/engine.py, umbra_core/runtime.py, tests/test_d006.py, .agent/*
- Next action: Task 11

## Repo facts needed now
- Mimir project: 7777645d52a91b49
- Mimir task: 2488863e760547a08bb9208b02764650
- Snapshot already included `social` (authoritative_state()) and load_organism already reconstructed it from prior tasks — Task 10's real gap was accepted_state()/replay-comparison + routine_handles bound
- routine_handles must be interrupted on hypothesis retirement (`_prune_hypotheses` now calls `interrupt_active_routine`) or they leak unbounded across the full hypothesis lifetime even though active hypotheses stay capped at 16
- PendingInteraction.execution_id (= Governance proposal_id) is plain uuid4, never seeded — excluded from SocialEngine.accepted_state() to keep birth-replay equality deterministic

## Last validation
- Command: pytest -q
- Result: 249 passed

## Open blockers
- mimir_validation_run task-scoped runner unavailable (same precedent as Tasks 4–9); mimir_task_close succeeded with locally-verified test results
