# CURRENT.md

## Active directive
- ID: D-20260723-1336-d008-gate8-frame-ring-readonly
- Project directive: UMBRA-D-008
- Goal: Fix Task 11 Gate 8 finding — renderers received the live `FrameRing` (public `push`/`clear`); `PresentationState`'s nested dicts were mutable in place despite `frozen=True`.
- Status: complete
- Acceptance: met — `FrameRingReader`/`FrameRing.read_only()` expose only `read_latest`; all renderers + tests retyped; `PresentationState` nested mappings frozen via `MappingProxyType` at construction; C7 hostile tests extended; full suite green (400 passed, 2 skipped — same pre-existing tkinter-display skips)
- Touched files: `umbra_core/expression/{frame_ring,renderer,headless_renderer,presentation_state,__init__}.py`, `ui/reference_companion/tkinter_renderer.py`, `experiments/d008/hostile_renderer.py`, `tests/test_d008.py`
- Next action: Task 12 (per plan `docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md`) — complete `tests/test_d008.py` minimum list + prior seals. Parent D-008 Mimir task remains open, controller owns lifecycle.

## Repo facts needed now
- `umbra_core/expression/frame_ring.py`: `FrameRing.read_only() -> FrameRingReader`. `FrameRingReader` (`__slots__`) wraps a live `FrameRing` and exposes only `read_latest(cursor)`, `__len__`, `__iter__`, `oldest_frame_id` — no `push`/`clear`, so a renderer that stores the reference across calls (as `HostileRenderer` now does) has no write method to find.
- `ReferenceRenderer.read_latest` (and `HeadlessRenderer`/`TkinterRenderer`/`HostileRenderer`) are now typed against `FrameRingReader`, not `FrameRing`. All callers must pass `ring.read_only()`, never the live ring, to a renderer.
- `PresentationState.__post_init__` (`umbra_core/expression/presentation_state.py`) wraps `visible_condition_channels`/`developmental_markers` in `MappingProxyType(dict(...))` via `object.__setattr__` — defensive copy then frozen, so in-place item assignment raises `TypeError` and cannot leak into the engine's own next-tick state or the ring's stored entry.
- `HostileRenderer.render()` now additionally attempts, and records as rejected: pushing/clearing via the held `FrameRingReader`, and item-assignment on both nested `PresentationState` mappings.
- Residual (unchanged, out of scope): reflection-based bypass via `object.__setattr__` on a frozen dataclass remains structurally possible in Python — not defended against, same as before.
- `umbra_core.expression.engine.ExpressionConfig(ignore_actions, ignore_individuality, ignore_physiology)` + `condition_to_expression_config(condition)` (raises `ExpressionConfigError` for C1/C2/C3/C7/C8) map D-008's C4/C5/C6 ablations — unchanged by this task.
- Plan: `docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md` (Task 11 checklist)
- Report: `.superpowers/sdd/task-11-report.md` (Gate 8 addendum appended; this file is gitignored — `.superpowers/sdd/.gitignore` excludes all task reports from git, not a new omission)
- Mimir task: `2373ade963c54fc29a78a92f4a5569b4` (this task, closed); parent D-008 task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open — controller owns lifecycle.

## Last validation
- Command: `pytest tests/test_d008.py -q` (90 passed, 2 skipped) then `pytest -q` full suite (400 passed, 2 skipped) — reproduced locally.
- `mimir_validation_run(pytest -q)` again rejected with "validation requires an active observed task" — same recurring precedent as Tasks 2-11.

## Open blockers
- `mimir_validation_run` remains blocked by "validation requires an active observed task" (recurring across Tasks 2-11 and this fix).
- This sandbox lacks `python3-tk`/a display — formal Tkinter soak (design §4 Gate 12 incremental cost) needs a machine/CI with real tkinter + display; not attempted here, not claimed.
- Parent Mimir task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open (do not close per directive).
