# CURRENT.md

## Active directive
- ID: D-20260722-1401-d006-task8-routines
- Project directive: UMBRA-D-006
- Goal: Task 8 — shared routines via D-005 procedural promotion
- Status: done
- Acceptance: met — routine_eligible after N independent contingent episodes; MemoryEngine.promote_social_routine; soft ordered proposals; interrupt_active_routine; C8 authored blocked; episode provenance test; 4 new tests + full suite green
- Touched files: umbra_core/social/engine.py, umbra_core/memory/engine.py, umbra_core/social/__init__.py, umbra_core/memory/__init__.py, tests/test_d006.py, .superpowers/sdd/task-8-report.md, .agent/*
- Next action: Task 9 (ablations C0–C9 + C3 isolated controller)

## Repo facts needed now
- Mimir project: 7777645d52a91b49
- Mimir task: 09de60f0ae00461e961223db74bf78eb
- Promotion auto-fires on 3rd contingent `resolve_pending` commit when episodes are independent (tick gap ≥ 32)
- C8 `scripted_routine=True` blocks eligibility; `authored=True` spec raises ValueError

## Last validation
- Command: pytest -q
- Result: 228 passed

## Open blockers
- mimir_validation_run task-scoped runner unavailable (same precedent as Tasks 4–7)
