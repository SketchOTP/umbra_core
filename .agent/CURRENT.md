# CURRENT.md

## Active directive
- ID: D-20260723-1231-d008-task9-tkinter-companion
- Project directive: UMBRA-D-008
- Goal: Tkinter reference companion over headless presentation model (`ui/reference_companion/`) — habitat canvas (shapes/orientation/posture/attention/icons only), diagnostics (capability/phase/versions/source-refs/condition-channels), `close()` unregisters cursor + destroys window + leaves organism running, thread-safe handoff for organism ticking off Tk thread, import isolation
- Status: complete
- Acceptance: met — 4 brief-named tests + 4 supporting tests pass; stdlib tkinter only; full suite 371 passed, 2 skipped (both skips are genuinely-missing-tkinter, not design gaps)
- Touched files: `ui/__init__.py`, `ui/reference_companion/{__init__,habitat_view,diagnostics,tkinter_renderer}.py` (new); `tests/test_d008.py` (+8 tests)
- Next action: Task 10 (per plan `docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md`) — parent D-008 Mimir task remains open, controller owns lifecycle

## Repo facts needed now
- `habitat_view.py`/`diagnostics.py` duck-type against a `CanvasLike` `Protocol` (`delete`/`create_oval`/`create_line`/`create_text`) and never import `tkinter` — fully unit-testable with a fake-canvas double, no display needed.
- `tkinter_renderer.py` imports `tkinter` lazily, only inside `TkinterRenderer.__init__` — importing `ui.reference_companion` never requires a Tk install; only instantiating a renderer does.
- Habitat canvas draws entities + body + orientation line + posture color + attention ring (only when `attention_target` non-null, i.e. already past the display-confidence threshold) + nonverbal icon — never capability/phase/version/source-ref/condition-channel text (verified by `test_habitat_canvas_excludes_capability_phase_version_diagnostics`). Diagnostics draws exactly those excluded fields on a separate canvas, hidden by default (`set_diagnostics_visible(False)`).
- `TkinterRenderer.close()` is idempotent: sets `_closed=True`, drops its `RendererCursor` (further `read_latest` calls return `None`), destroys only the two canvases it created (+ the root `Tk()` window if it created one rather than being handed a `master`) — never touches organism/adapter/`ExpressionEngine`.
- Thread-safety contract: `TkinterRenderer.ring_lock` (`threading.Lock`) is acquired inside `read_latest`; a harness driving `Organism.tick_once()` on a separate thread is expected to acquire the same lock around each tick — explicit handoff boundary, zero changes to `FrameRing` itself.
- This dev sandbox has **no `python3-tk` package installed** (`import tkinter` → `ModuleNotFoundError`, independent of `DISPLAY`) and `sudo apt-get install python3-tk` requires interactive auth unavailable here — the 2 tests needing a real `TkinterRenderer` instance (`test_reference_interface_runs_without_diagnostics`, `test_tkinter_renderer_close_leaves_organism_running`) use `pytest.importorskip("tkinter")` (+ `TclError` skip for no-display) and honestly skip here; they run for real wherever tkinter is installed.
- Plan: `docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md` (Task 9 checklist)
- Report: `.superpowers/sdd/task-9-report.md`
- Mimir task: `35bad317472b4204b1c80c12c0670ceb` (Task 9 sub-task, closed); parent D-008 task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open — controller owns lifecycle.

## Last validation
- Command: `pytest tests/test_d008.py -q` (61 passed, 2 skipped) then `pytest tests/ -q` (371 passed, 2 skipped) — reproduced locally.
- `mimir_validation_run` again rejected allowlisted `pytest -q` with "validation requires an active observed task" even after an intervening `mimir_task_observe` — same recurring precedent as Tasks 2-8.

## Open blockers
- `mimir_validation_run` remains blocked by "validation requires an active observed task" (recurring across Tasks 2-9).
- This sandbox lacks `python3-tk`/a display — formal Tkinter soak (design §4 Gate 12 incremental cost) needs a machine/CI with real tkinter + display; not attempted here, not claimed.
- Parent Mimir task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open (do not close per directive).
