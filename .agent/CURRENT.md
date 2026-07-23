# CURRENT.md

## Active directive
- ID: D-20260723-1349-d008-gate8-remove-ring-from-renderers
- Project directive: UMBRA-D-008
- Goal: Fix remaining Important Gate 8 finding — `FrameRingReader` still exposed the live `FrameRing` via its own `_ring` attribute, so a renderer holding a reader could call `reader._ring.push()`.
- Status: complete
- Acceptance: met — deleted `FrameRingReader`/`FrameRing.read_only()` entirely; `ReferenceRenderer` protocol is now `render(entry)`/`set_diagnostics_visible(bool)`/`close()` only, no method anywhere accepts a ring/reader argument; `HeadlessRenderer`/`TkinterRenderer`/`HostileRenderer` updated (dropped `_cursor`/`ring_lock`/`poll_and_render`/`schedule`/`read_latest`); every test call site now polls via its own `RendererCursor` + `FrameRing.read_latest(cursor)` before calling `renderer.render(entry)`; hostile test asserts no `_ring`/`ring` attribute and no ring/reader parameter anywhere; full suite green (400 passed, 2 skipped — same pre-existing tkinter-display skips)
- Touched files: `umbra_core/expression/{frame_ring,renderer,headless_renderer,__init__}.py`, `ui/reference_companion/tkinter_renderer.py`, `experiments/d008/hostile_renderer.py`, `tests/test_d008.py`
- Next action: Task 12 (per plan `docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md`). Parent D-008 Mimir task remains open, controller owns lifecycle.

## Repo facts needed now
- `umbra_core/expression/frame_ring.py`: `FrameRingReader`/`FrameRing.read_only()` no longer exist. `FrameRing.read_latest(cursor)` is unchanged and is called directly by trusted callers only (organism runtime, test-as-poller, future UI driver) — never by a renderer.
- `umbra_core/expression/renderer.py`: `ReferenceRenderer` protocol is exactly `render(entry: FrameRingEntry)`, `set_diagnostics_visible(visible: bool)`, `close()`. No `read_latest`, no ring/reader parameter on any method — this is the structural fix, not a convention.
- `HeadlessRenderer`/`TkinterRenderer`/`HostileRenderer` (`umbra_core/expression/headless_renderer.py`, `ui/reference_companion/tkinter_renderer.py`, `experiments/d008/hostile_renderer.py`) hold no cursor, no ring, no reader — only their own render-count/last-error bookkeeping. `TkinterRenderer` dropped `ring_lock`/`poll_and_render`/`schedule` (unused outside tests; a future real UI driver would own the ring+cursor+lock itself and call `renderer.render(entry)`, never handing the renderer the ring).
- `tests/test_d008.py`: every former `renderer.read_latest(org.frame_ring.read_only())` call site is now `cursor = RendererCursor(...); org.frame_ring.read_latest(cursor)` followed by `renderer.render(entry)`. New `test_reference_renderer_protocol_has_no_ring_channel` asserts `render`'s only parameter is `entry` for `HeadlessRenderer`/`HostileRenderer`/`TkinterRenderer`/`ReferenceRenderer` itself, and that none of them have `read_latest`/`poll_from`. `test_hostile_renderer_write_attempts_are_rejected` now asserts `not hasattr(hostile, "_ring")`/`"ring"` and that `render`'s signature is exactly `(self, entry)`.
- Removed the old `test_frame_ring_reader_has_no_push_or_clear` test (its subject, `FrameRingReader`, no longer exists) — superseded by the structural no-ring-channel test above.
- Plan: `docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md` (Task 11 checklist)
- Report: `.superpowers/sdd/task-11-report.md` (Gate 8 follow-up addendum to be appended; this file is gitignored — `.superpowers/sdd/.gitignore` excludes all task reports from git, not a new omission)
- Mimir task: `dece0564f7524f82b5efec9b203048bd` (this task); parent D-008 task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open — controller owns lifecycle.

## Last validation
- Command: `pytest tests/test_d008.py -q` (90 passed, 2 skipped) then `pytest -q` full suite (400 passed, 2 skipped) — reproduced locally.
- `mimir_validation_run(pytest -q)` again rejected with "validation requires an active observed task" — same recurring precedent as Tasks 2-11 and the prior Gate 8 fix.

## Open blockers
- `mimir_validation_run` remains blocked by "validation requires an active observed task" (recurring across Tasks 2-11 and both Gate 8 fixes).
- This sandbox lacks `python3-tk`/a display — formal Tkinter soak (design §4 Gate 12 incremental cost) needs a machine/CI with real tkinter + display; not attempted here, not claimed.
- Parent Mimir task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open (do not close per directive).
