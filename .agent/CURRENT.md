# CURRENT.md

## Active directive
- ID: D-20260723-1130-d008-task6-frame-ring
- Project directive: UMBRA-D-008
- Goal: FrameRing with embedded full RenderPacket snapshots (habitat included at derive time), bounded by frozen D-008 thresholds, non-destructive renderer cursors, stale rejection by generation/state-version/execution; no runtime/Tkinter wiring
- Status: complete — 6 Task 6 tests pass; full suite green (346 passed)
- Acceptance: met
- Touched files: `umbra_core/expression/frame_ring.py` (new), `umbra_core/expression/__init__.py`, `tests/test_d008.py`, `.superpowers/sdd/task-6-report.md`
- Next action: Task 7 — runtime wiring (controller-owned parent D-008 Mimir task remains open)

## Repo facts needed now
- `umbra_core/expression/engine.py`: `ExpressionEngine.derive(view: ExpressionView) -> RenderPacket`, stateful only in `_last_presentation` (for posture-transition tracking) — no other side effects, no writes.
- `ExpressionView` is a frozen dataclass of already-extracted plain data (physiology dict, `AttentionView`, `AttachmentView`, `embodiment_state` dict, `LastOutcomeView | None`) — never a live `Governance`/`Embodiment`/`Physiology` reference.
- Denied (`LastOutcomeView.admitted=False`) vs failed (`admitted=True, success=False`) are rendered differently: denied -> IDLE/no active_capability; failed -> posture/action_phase=INTERRUPTED with active_capability still set.
- `HabitatReadModel.from_embodiment_state` reads `Embodiment.to_state()["habitat"]` directly (features + partners), bounded by frozen `habitat_read_model_max_entities` (64).
- Task 6 must store the full `RenderPacket` on each `FrameRingEntry`; renderers must never rebuild habitat when reading old frames.
- Stale frames are rejected against current validity predicates: body/profile generation, state version, and active execution.
- Design Supplement S1 (`docs/superpowers/specs/2026-07-23-umbra-d008-coherent-digital-embodiment-design.md:482-541`) authorizes clamping continuous body params on production profiles instead of hard-rejecting; implemented in `umbra_core/embodiment_adapters/adapter.py` (`_translate_continuous_limits`), commits `2460415`/`ca97821`.
- The prior Important finding (max_step=1.0 vs real 1.2-1.8 arbitration fallback steps causing near-total immobility when `embodiment_adapter_enabled=True`) is now resolved by clamping — independently re-verified by re-running the original failing probe against the fixed code.
- `OrganismConfig.embodiment_adapter_enabled` stays default `False` (opt-in) — this is now acceptable specifically because the enabled path is proven safe (regression test + independent probe), not because a defect is hidden behind the flag.
- Non-clampable marker convention: `BodyProfile.physical_limits["<limit>_clampable"] = False` (absent ⇒ clampable) — chosen to avoid changing `profile_definition_hash` for frozen production profiles.
- Plan: docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md
- Mimir task: 134c0977bec34112b5fada9145c06ee5 (Task 6 sub-task; parent D-008 task cbbb61834c98463cb70fb9254ba08ea2 not closed — controller owns lifecycle)

## Last validation
- Command: pytest tests/test_d008.py -q; pytest -q
- Result: pass (36 passed; 346 passed full suite) — reproduced locally; `mimir_validation_run` blocked (see below)

## Open blockers
- `mimir_validation_run` rejected scoped command as not allowlisted and allowlisted `pytest -q` with "validation requires an active observed task"; local pytest validation passed.
- Parent Mimir task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open.
