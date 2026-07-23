# CURRENT.md

## Active directive
- ID: D-20260723-1219-d008-task8-review-fix
- Project directive: UMBRA-D-008
- Goal: Fix Task 8 review Important findings — load_organism must fail closed on missing/corrupted D-008 attachment events; strengthen birth-replay test to exercise the real migration/restart path instead of re-invoking attachment_state_from_event on its own output
- Status: complete — 1-line production fix (gated store.validate_chain() call) + 2 tests strengthened; full suite green (365 passed, zero skips)
- Acceptance: met
- Touched files: `umbra_core/runtime.py` (load_organism), `tests/test_d008.py` (2 tests rewritten, unused imports removed)
- Next action: Task 9 — Tkinter reference companion (parent D-008 Mimir task remains open, per controller ownership)

## Repo facts needed now
- Root cause of the Task 8 review finding: `load_organism` never called `store.validate_chain()` before reconstructing D-008 attachment from the ledger. Deleting the sole `embodiment_body_attached` row made `store.last_event_of_types(ATTACHMENT_EVENT_TYPES)` legitimately return `None` — indistinguishable from a genuine pre-D-008 (never-attached) organism — so `attachment_state_from_event(None)` silently returned a fresh `DETACHED`/generation-0 state and `maybe_migrate_d008_attachment` would re-migrate a body that had already executed authoritative actions (fail-open, not fail-closed).
- Fix: `umbra_core/runtime.py::load_organism` now calls `store.validate_chain()` immediately before the D-008 attachment-reconstruction block, gated on `config.embodiment_adapter_enabled` — a tampered/corrupted chain now raises `PersistenceError` there instead of falling through to the "never attached" default. Only `tests/test_d008.py` sets `embodiment_adapter_enabled=True` anywhere in the repo, so this is zero behavior/perf change for D-001..D-007 callers.
- `test_missing_embodiment_event_fails_closed` now additionally asserts `load_organism(cfg)` itself raises `PersistenceError` (previously only checked `store.validate_chain()` in isolation).
- `test_birth_replay_matches_authoritative_transitions` now builds a legacy pre-D-008 DB via `_create_legacy_pre_d008_db`, calls `load_organism` (triggering `maybe_migrate_d008_attachment`, origin `D008_MIGRATION`), performs two swaps, then calls `load_organism` a second time and asserts the reloaded adapter's `AttachmentState` matches the live adapter byte-for-byte, plus `replay_from_birth(db_path)["chain_valid"]`. No longer calls `attachment_state_from_event` directly.
- Migration idempotency (`test_d008_migration_second_load_is_noop`, `test_d008_migration_event_is_part_of_valid_replay_chain`) reconfirmed unaffected by the new `validate_chain()` call.
- Plan: docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md (Task 8 checklist)
- Report: `.superpowers/sdd/task-8-report.md` (fix notes appended under "Review fix — Important findings")
- Mimir task: d6ce3d9574cf4ffc84c687bce4298324 (this fix sub-task, closed); parent D-008 task cbbb61834c98463cb70fb9254ba08ea2 intentionally left open — controller owns lifecycle.

## Last validation
- Command: `pytest tests/test_d008.py -q` (55 passed) then `pytest tests/ -q` (365 passed, zero skips) — reproduced locally.
- `mimir_validation_run` again rejected allowlisted `pytest -q` with "validation requires an active observed task" even after an intervening `mimir_task_observe` — same recurring precedent as Tasks 2-8. Validated locally instead.

## Open blockers
- `mimir_validation_run` remains blocked by "validation requires an active observed task" (recurring across Tasks 2-8 and this fix).
- Parent Mimir task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open (do not close per directive).
