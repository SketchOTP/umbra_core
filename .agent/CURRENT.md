# CURRENT.md

## Active directive
- ID: D-20260723-1117-d008-task5-expression
- Project directive: UMBRA-D-008
- Goal: PresentationState + HabitatReadModel + ExpressionEngine.derive(ExpressionView)->RenderPacket (Task 5) — body-neutral, no mood/emotion authority; do not wire into runtime tick (Task 7) or build FrameRing (Task 6)
- Status: complete — 8 brief-named tests + 2 supporting tests pass; full suite green (340 passed)
- Acceptance: met
- Touched files: `umbra_core/expression/{presentation_state,habitat_read_model,engine,__init__}.py` (new), `tests/test_d008.py`
- Next action: Task 6 — FrameRing with embedded RenderPacket; parent D-008 Mimir task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open (controller owns lifecycle)

## Repo facts needed now
- `umbra_core/expression/engine.py`: `ExpressionEngine.derive(view: ExpressionView) -> RenderPacket`, stateful only in `_last_presentation` (for posture-transition tracking) — no other side effects, no writes.
- `ExpressionView` is a frozen dataclass of already-extracted plain data (physiology dict, `AttentionView`, `AttachmentView`, `embodiment_state` dict, `LastOutcomeView | None`) — never a live `Governance`/`Embodiment`/`Physiology` reference.
- Denied (`LastOutcomeView.admitted=False`) vs failed (`admitted=True, success=False`) are rendered differently: denied -> IDLE/no active_capability; failed -> posture/action_phase=INTERRUPTED with active_capability still set.
- `HabitatReadModel.from_embodiment_state` reads `Embodiment.to_state()["habitat"]` directly (features + partners), bounded by frozen `habitat_read_model_max_entities` (64).
- Design Supplement S1 (`docs/superpowers/specs/2026-07-23-umbra-d008-coherent-digital-embodiment-design.md:482-541`) authorizes clamping continuous body params on production profiles instead of hard-rejecting; implemented in `umbra_core/embodiment_adapters/adapter.py` (`_translate_continuous_limits`), commits `2460415`/`ca97821`.
- The prior Important finding (max_step=1.0 vs real 1.2-1.8 arbitration fallback steps causing near-total immobility when `embodiment_adapter_enabled=True`) is now resolved by clamping — independently re-verified by re-running the original failing probe against the fixed code.
- `OrganismConfig.embodiment_adapter_enabled` stays default `False` (opt-in) — this is now acceptable specifically because the enabled path is proven safe (regression test + independent probe), not because a defect is hidden behind the flag.
- Non-clampable marker convention: `BodyProfile.physical_limits["<limit>_clampable"] = False` (absent ⇒ clampable) — chosen to avoid changing `profile_definition_hash` for frozen production profiles.
- Plan: docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md
- Mimir task: 94e20792b4634fe197411a50e345b0cd (re-review sub-task; parent D-008 task cbbb61834c98463cb70fb9254ba08ea2 not closed — controller owns lifecycle)

## Last validation
- Command: pytest tests/test_d008.py -q; pytest -q
- Result: pass (30 passed; 340 passed full suite) — reproduced locally; `mimir_validation_run` blocked (see below)

## Open blockers
- `mimir_validation_run` rejected allowlisted `pytest -q` with "validation requires an active observed task" — same recurring precedent as prior D-006/D-008 tasks; validated locally instead.
- None blocking. Task 5 (ExpressionEngine) is complete; Task 6 (FrameRing) is next.
