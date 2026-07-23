# CURRENT.md

## Active directive
- ID: D-20260723-1330-d008-task11-isolated-ablations
- Project directive: UMBRA-D-008
- Goal: Isolate ablation conditions C1-C10 (Task 11 of the D-008 plan) — C1/C2/C3 diagnostic controllers, C7 hostile-renderer test double, C4/C5/C6 production ExpressionConfig switches, C8 disposable-DB-only guard.
- Status: complete
- Acceptance: met — brief-named tests (`test_scripted_animation_condition_is_isolated`, `test_random_expression_condition_is_isolated`, `test_scalar_mood_controller_is_isolated`) pass, plus C7/C8 coverage; full suite green (398 passed, 2 skipped — same pre-existing tkinter-display skips)
- Touched files: `experiments/d008/{diagnostic_controllers,hostile_renderer}.py` (new), `umbra_core/expression/{presentation_state,engine,__init__}.py`, `umbra_core/runtime.py`, `tests/test_d008.py`
- Next action: Task 12 (per plan `docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md`) — complete `tests/test_d008.py` minimum list + prior seals. Parent D-008 Mimir task remains open, controller owns lifecycle.

## Repo facts needed now
- `umbra_core.expression.engine.ExpressionConfig(ignore_actions, ignore_individuality, ignore_physiology)` + `condition_to_expression_config(condition)` (raises `ExpressionConfigError` for C1/C2/C3/C7/C8) map D-008's C4/C5/C6 ablations. `ExpressionEngine.__init__(config=None)` stores it; `_derive_presentation` routes physiology/individuality through `_effective_physiology`/`_effective_individuality_summary` in BOTH the DETACHED and ATTACHED branches, and forces `outcome = None` when `ignore_actions` is set (C4) — actions still execute in `Embodiment`/`Governance`, only the *derived presentation* goes blind.
- `OrganismConfig.expression_config: ExpressionConfig | None = None` is an **explicit-override-only** field (same pattern as `social_config`/`individuality_config`) — `Organism.__init__` never auto-calls `condition_to_expression_config(config.condition)`, because `condition` is already overloaded by D-002..D-007's own `condition_to_*_config` functions and many existing tests (`test_d002/d003/d005/d006/d007.py`) build organisms with `condition` in `C1..C8` while `expression_enabled` defaults `True` — auto-wiring would raise `ExpressionConfigError` for all of them. Callers that want a D-008 expression ablation must pass `expression_config=condition_to_expression_config(cond)` explicitly.
- `PresentationState` is now `@dataclass(frozen=True)` (`umbra_core/expression/presentation_state.py`) — the same instance is both `ExpressionEngine._last_presentation` and the object stored in the shared `FrameRing`, so an unfrozen field assignment by any renderer would corrupt the engine's own next-tick `prior_posture`/transition bookkeeping. Verified only two construction sites exist in the whole repo (both inside `_derive_presentation`), nothing mutates one in place. Residual (documented, not fixed): nested mutable dict fields (`visible_condition_channels`/`developmental_markers`) and `object.__setattr__` reflection bypass are not defended against; `ReferenceRenderer.read_latest(ring)` hands renderers the live `FrameRing` object including its public `push()` — a structural write channel, not per-field — left for Task 13's Gate 8 sizing.
- `experiments/d008/diagnostic_controllers.py`: C1 `ScriptedAnimationScheduler`, C2 `RandomPresentationController`, C3 `ScalarMoodController`, `assert_not_production_schema`; `assert_disposable_db_path(db_path)` (C8) raises `ValueError` unless the path resolves under the system temp dir or directly under `experiments/d008/`.
- `experiments/d008/hostile_renderer.py`: `HostileRenderer` (C7) — same `ReferenceRenderer` shape as `HeadlessRenderer`, never constructed with an organism/embodiment/physiology/governance reference; `render()` attempts ordinary attribute writes on `PresentationState`/`HabitatReadModel`/`RenderPacket`/`FrameRingEntry` fields and records `attempted_writes`/`rejected_writes`/`successful_writes`.
- Plan: `docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md` (Task 11 checklist)
- Report: `.superpowers/sdd/task-11-report.md`
- Mimir task: `b184e9b1adc44cab8046c3de1eaf4163` (this task, closed v3); parent D-008 task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open — controller owns lifecycle.

## Last validation
- Command: `pytest tests/test_d008.py -q` (88 passed, 2 skipped) then `pytest tests/ -q` (398 passed, 2 skipped) — reproduced locally.
- `mimir_validation_run` again rejected allowlisted `pytest -q` with "validation requires an active observed task" even after an intervening `mimir_task_observe` — same recurring precedent as Tasks 2-10.

## Open blockers
- `mimir_validation_run` remains blocked by "validation requires an active observed task" (recurring across Tasks 2-11).
- This sandbox lacks `python3-tk`/a display — formal Tkinter soak (design §4 Gate 12 incremental cost) needs a machine/CI with real tkinter + display; not attempted here, not claimed.
- Parent Mimir task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open (do not close per directive).
- `ReferenceRenderer.read_latest(ring)` grants renderers the live `FrameRing` object (including its public `push()`), a structural write channel not exercised by `HostileRenderer` — Task 13's Gate 8 evidence run should size whether this needs a read-only ring view.
