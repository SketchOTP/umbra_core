# CURRENT.md

## Active directive
- ID: D-20260723-0942-d008-task4-migration
- Project directive: UMBRA-D-008
- Goal: Task 4 — D-007→D-008 attachment migration (`maybe_migrate_d008_attachment`)
- Status: complete — 7 new tests pass; full suite green (327 passed)
- Acceptance: pre-D008 schema detected via ledger (no `embodiment_body_*` events); frozen `default_migration_profile_id` (ABSTRACT_SHAPE_BODY) attached with `origin=D008_MIGRATION` + schema version, atomic single-event commit, idempotent, stable `body_instance_id`, no phys/memory/social/individuality/habitat reset, post-migration missing attachment fails closed, birth replay includes migration event with no re-inference
- Touched files: umbra_core/embodiment_adapters/{adapter,profiles,__init__}.py, umbra_core/{runtime,persistence}.py, tests/test_d008.py, .superpowers/sdd/task-4-report.md, .agent/*
- Next action: Task 5 — ExpressionEngine (not built in this task)

## Repo facts needed now
- `OrganismConfig.embodiment_adapter_enabled` defaults `False` — adapter/migration are opt-in; unconditional wiring regressed D-001..D-004 (ABSTRACT_SHAPE_BODY.max_step=1.0 vs 1.2-1.8 arbitration search steps). Callers must set the flag to exercise attach/migration/adapter-rejection paths.
- Pre-D008 detection is ledger-based: `store.last_event_of_types(ATTACHMENT_EVENT_TYPES)` (new `persistence.py` helper + `idx_events_event_type` index), not snapshot shape.
- Plan: docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md
- Mimir task: ca071261c6bc4a79b1c7cca3afedeb97 (Task 4 sub-task; parent D-008 task cbbb61834c98463cb70fb9254ba08ea2 not closed — controller owns lifecycle)

## Last validation
- Command: pytest -q
- Result: pass (327 passed)

## Open blockers
- mimir_validation_run recurring "validation requires an active observed task" — validated locally instead (same precedent as prior D-006/D-008 tasks).
- None blocking for Task 4. ExpressionEngine (Task 5+) and UI (Task 9) remain out of scope.
