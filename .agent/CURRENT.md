# CURRENT.md

## Active directive
- ID: D-20260723-1056-d008-s1-clamp-fix
- Project directive: UMBRA-D-008
- Goal: Fix Task 4 review Important finding — clamp continuous body limits in `EmbodimentAdapter` per design Supplement S1 (operator decision A), instead of hard-rejecting oversize `step`
- Status: complete — clamp implemented; constrained profile keeps hard-reject path; 3 new tests pass; full suite green (330 passed)
- Acceptance: production profiles clamp oversize continuous params (not fail) with requested/applied/translation evidence + body_profile_id/profile_definition_hash; `BODY_LIMIT_REJECTED` reserved for malformed/non-finite/non-positive/non-clampable; `CONSTRAINED_TEST_BODY.max_step` marked non-clampable; D-001 fallback MOVE steps (1.2–1.8) succeed with `embodiment_adapter_enabled=True`; no mutation of `AdapterRequest.params`; production profile hashes untouched
- Touched files: `umbra_core/embodiment_adapters/adapter.py`, `experiments/d008/constrained_profile.py`, `umbra_core/runtime.py` (comment only), `tests/test_d008.py`, `.superpowers/sdd/task-4-report.md`, `.agent/{CURRENT,DIRECTIVES,OUTCOMES}.md`
- Next action: Task 5 — ExpressionEngine (not built in this task); parent D-008 Mimir task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open per instruction

## Repo facts needed now
- Design Supplement S1 (`docs/superpowers/specs/2026-07-23-umbra-d008-coherent-digital-embodiment-design.md`, already committed by prior session) authorizes clamping continuous params instead of hard-rejecting; this task implements it.
- Non-clampable marker convention: `BodyProfile.physical_limits["<limit>_clampable"] = False` (absent ⇒ clampable). Chosen over a new `BodyProfile` dataclass field specifically to avoid changing `profile_definition_hash` for the two frozen production profiles.
- `OrganismConfig.embodiment_adapter_enabled` stays default `False` (opt-in) — flipping it would break `test_embodiment_adapter_disabled_by_default_preserves_prior_behavior`; the adapter is already wired into `governance.execute_and_verify`, so `enabled=True` callers get real clamped execution.
- Plan: docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md
- Mimir task: 2bd97b3484d04272b4ce07b0f9b65dd4 (Supplement S1 fix sub-task; parent D-008 task cbbb61834c98463cb70fb9254ba08ea2 not closed — controller owns lifecycle)

## Last validation
- Command: pytest tests/test_d008.py -q; pytest -q
- Result: pass (20 passed; 330 passed) — reproduced locally; `mimir_validation_run` blocked (see below)

## Open blockers
- `mimir_validation_run` rejected allowlisted `pytest -q` with "validation requires an active observed task" — same recurring precedent as prior D-006/D-008 tasks; validated locally instead.
- Previously-open design-level `max_step` vs. arbitration fallback-step conflict is now resolved by this clamp fix (no longer a blocker to enabling the adapter for real use, though the default flag stays opt-in for the reason above).
