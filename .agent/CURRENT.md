# CURRENT.md

## Active directive
- ID: D-20260723-1141-d008-task7-runtime-wire
- Project directive: UMBRA-D-008
- Goal: Wire ExpressionEngine side-car (derive->FrameRing.push) into Organism.tick_once after outcome commit using copied snapshots; expose frame_ring; ReferenceRenderer protocol + HeadlessRenderer; gate on OrganismConfig.expression_enabled/C10; no Tkinter (Task 9)
- Status: complete — 5 brief-named tests + 4 supporting tests pass (43 in test_d008.py); full suite green (353 passed)
- Acceptance: met
- Touched files: `umbra_core/runtime.py`, `umbra_core/expression/{renderer,headless_renderer,__init__}.py` (new/modified), `tests/test_d008.py`, `.superpowers/sdd/task-7-report.md`
- Next action: Task 8 — restart, replay, body-swap continuity (controller-owned parent D-008 Mimir task remains open)

## Repo facts needed now
- `Organism.__init__` always builds `self.expression_engine = ExpressionEngine()` and `self.frame_ring = FrameRing.from_thresholds()` — cheap, read-only, never in `authoritative_state()`/snapshots.
- `Organism._push_expression_frame(last_outcome)` is the only writer to `frame_ring`; it is called at both `tick_once` return sites (external-displacement early return, and the main end-of-tick return), guarded by `self._expression_active()` and wrapped in try/except (side-car failure never pauses the tick loop — same containment pattern as D-005 memory consolidation).
- `ExpressionView` is built from `self.phys.as_dict()` and `self.embodiment.to_state()` — both fresh dict copies (verified by `to_state()` source read), never live subsystem references (Task 5 review watch item, now exercised at the runtime wire by `test_expression_view_is_built_from_copied_snapshots_not_live_aliases`).
- A local `committed_outcome` in `tick_once` tracks whichever `VerifiedOutcome` was actually committed this tick (a delayed-from-last-tick completion via `Embodiment.tick_actuation`, or this tick's own immediate `execute_and_verify`) — a plain governance denial is rendered as `LastOutcomeView(capability=cand.capability, admitted=False)`, never as executed; an admitted-but-still-delayed candidate renders as `None` (nothing verified yet).
- `FrameRingEntry.active_execution_id` is always `None` for runtime-pushed frames. Setting it to the outcome's execution id would break ordinary polling: `FrameRing._is_valid_for_cursor` requires an exact match on `cursor.active_execution_id` whenever `entry.active_execution_id` is non-None, and a default `RendererCursor` never pre-knows same-tick execution ids. That field is reserved for a still-pending multi-tick actuation.
- `OrganismConfig.expression_enabled: bool = True` (unlike `embodiment_adapter_enabled`, which stays opt-in) — safe default because the side-car is strictly additive/read-only and appends zero authoritative events (proven by `test_habitat_state_is_not_duplicated` comparing event-type sequences with the flag on vs off). Condition `"C10"` (design §4 frozen performance baseline) always forces expression off regardless of the flag, via `Organism._expression_active()`.
- `ReferenceRenderer` (`umbra_core/expression/renderer.py`, a `Protocol`) and `HeadlessRenderer` (`umbra_core/expression/headless_renderer.py`) are structurally decoupled from the organism: `Organism`/`tick_once` never call a renderer, so renderer failure/closure/slowdown cannot pause the organism by construction. `HeadlessRenderer.read_latest` returns `None` (renders nothing) when no new valid frame exists — it can never fake continued autonomy.
- Plan: docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md
- Mimir task: 0218a285ae1d4f8cb1e62256569c2c03 (Task 7 sub-task; parent D-008 task cbbb61834c98463cb70fb9254ba08ea2 not closed — controller owns lifecycle)

## Last validation
- Command: pytest tests/test_d008.py -q; pytest -q
- Result: pass (43 passed; 353 passed full suite) — reproduced locally; `mimir_validation_run` blocked (see below)

## Open blockers
- `mimir_validation_run` rejected allowlisted `pytest -q` with "validation requires an active observed task" (same recurring precedent as Tasks 2-6); validated locally instead.
- Parent Mimir task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open.
