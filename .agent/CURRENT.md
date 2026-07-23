# CURRENT.md

## Active directive
- ID: D-20260723-1247-d008-task10-signals-individuality
- Project directive: UMBRA-D-008
- Goal: Map SIGNAL_PLAY/SIGNAL_ASSISTANCE, individuality-history differences, learned habits, shared routines, recovery, orientation, and cosmetic motion into `ExpressionEngine`'s visible expression channels — bounded, non-authoritative nudges only; no invented mood authority; signals never touch relationship state
- Status: complete
- Acceptance: met — 10 brief-named tests pass; full suite green (381 passed, 2 skipped — same pre-existing tkinter-display skips)
- Touched files: `umbra_core/expression/engine.py` (`_visible_condition_channels` now reads `ExpressionView.individuality_summary`), `tests/test_d008.py` (+10 tests, `_expression_view` helper gained `individuality_summary`/`embodiment` params)
- Next action: Task 11 (per plan `docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md`) — parent D-008 Mimir task remains open, controller owns lifecycle

## Repo facts needed now
- `ExpressionView.individuality_summary` (existing field, previously unused) is now read by the engine: `{"disposition_vector": {dim: float, ...}}` (from D-007 `IndividualityEngine.disposition_vector()`, values in [-1,1]) plus optional `"habit_active"`/`"routine_active"` booleans. Runtime does NOT populate this field yet (out of Task 10's file scope — brief named only `engine.py` + `tests/test_d008.py`); wiring `Organism._push_expression_frame` to pass real individuality/memory/social state into `individuality_summary` is a natural Task 11+ follow-up if desired, not required by any current test.
- Bounds: `INDIVIDUALITY_CHANNEL_BIAS_MAX = 0.15` (disposition-driven: persistence/rest_frequency/activity_intensity), `HABIT_ROUTINE_CHANNEL_BIAS = 0.10` (habit→transition_speed, routine→attentional_persistence, independent of each other). All channels stay clamped to [0,1]; individuality/habit/routine never changes `posture`/`active_capability`/`nonverbal_signal` for an identical outcome — verified by `test_renderer_does_not_create_authored_personality`.
- SIGNAL_PLAY/SIGNAL_ASSISTANCE (nonverbal_signal + INTERACTING posture), CHARGE→RECOVERING→resumed-ACTIVE, and orientation pass-through from `Embodiment.body.heading` were already correct from Tasks 5/7 — Task 10 added regression tests only, zero production changes needed for those three.
- `ExpressionEngine.derive(self, view)` signature is unchanged (still exactly `["self", "view"]`) — structurally has no path to a Social/relationship object, so signals cannot change relationship state by construction, not just by convention.
- Plan: `docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md` (Task 10 checklist)
- Report: `.superpowers/sdd/task-10-report.md`
- Mimir task: `aae19ea8b29843348a7eafcc6e7df06b` (Task 10 sub-task, closed); parent D-008 task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open — controller owns lifecycle.

## Last validation
- Command: `pytest tests/test_d008.py -q` (71 passed, 2 skipped) then `pytest tests/ -q` (381 passed, 2 skipped) — reproduced locally.
- `mimir_validation_run` again rejected allowlisted `pytest -q` with "validation requires an active observed task" even after an intervening `mimir_task_observe` — same recurring precedent as Tasks 2-9.

## Open blockers
- `mimir_validation_run` remains blocked by "validation requires an active observed task" (recurring across Tasks 2-10).
- This sandbox lacks `python3-tk`/a display — formal Tkinter soak (design §4 Gate 12 incremental cost) needs a machine/CI with real tkinter + display; not attempted here, not claimed.
- Parent Mimir task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open (do not close per directive).
