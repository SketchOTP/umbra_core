# CURRENT.md

## Active directive
- ID: D-20260723-1200-d008-task8-continuity
- Project directive: UMBRA-D-008
- Goal: Prove restart, replay, and body-swap continuity contracts listed in Task 8 brief; fix Task 7 inline-import lint
- Status: complete — 12 new tests + Task 7 import fix; full suite green (365 passed, zero skips)
- Acceptance: met
- Touched files: `tests/test_d008.py` (Task 7 inline-import moved to top; 12 new Task 8 tests appended)
- Next action: Task 9 — Tkinter reference companion (parent D-008 Mimir task remains open, per controller ownership)

## Repo facts needed now
- All nine Task 8 continuity contracts held with **zero production code changes** — only tests were needed:
  - `test_restart_preserves_body_position` / `test_snapshot_replay_matches`: `Embodiment.to_state()/from_state()` (D-001) + `EmbodimentAdapter` ledger-authoritative reconstruction (Task 4's `attachment_state_from_event` off `store.last_event_of_types`) already round-trip byte-identically.
  - `test_restart_preserves_visible_condition`: `visible_condition_channels` is a pure function of already-restored physiology/attention (`umbra_core/expression/engine.py::_visible_condition_channels`) — a fresh `ExpressionEngine` post-restart derives the same channels as one derived pre-close, with no dependency on the (intentionally non-persisted) `ExpressionEngine._last_presentation` in-memory field.
  - `test_interrupted_action_resolves_after_restart`: `_push_expression_frame`'s `last_outcome` is derived fresh every tick from that tick's own `committed_outcome`/`decision` — never carried state — so a forced `movement_reliability=0.0` INTERRUPTED frame pre-restart never leaks into the freshly-rebuilt (empty) frame ring post-restart; the next successful outcome renders EXECUTED normally.
  - `test_birth_replay_matches_authoritative_transitions`: attach + 2 swaps (3 authoritative `embodiment_body_*` events) replay through the same `attachment_state_from_event` helper `load_organism` uses and reconstruct the live adapter's exact `AttachmentState`.
  - `test_missing_embodiment_event_fails_closed`: deleting the `embodiment_body_attached` row breaks `Store.validate_chain()`'s ordinary sequence-gap check (same mechanism as D-002V/D-006's own "missing authoritative event" tests) — attachment integrity rides the same hash chain as every other authoritative event, no bespoke embodiment-specific validation needed.
  - `test_body_profile_swap_preserves_{identity,memory,relationships,individuality}`: `EmbodimentAdapter.swap_profile` only appends its own authoritative event + updates `AttachmentState` — it has no code path touching `ConstitutionalIdentity`, `MemoryEngine`, `SocialEngine`, or `IndividualityEngine`, confirmed by exact before/after state equality.
  - `test_avatar_identifier_absent_from_constitutional_identity`: `ConstitutionalIdentity` dataclass fields are fixed (agent_id/lineage_id/birth_event_id/schema_version/created_at/lifecycle_sequence/identity_commitment) — none avatar/body/UI-named; swap leaves `agent_id`/`identity_commitment` unchanged.
  - `test_ui_identifier_absent_from_individuality_state`: `IndividualityEngine.FORBIDDEN_STATE_KEYS` (from D-007) already contains `avatar_id`/`ui_component_id`/`screen_coordinates`/`animation_name` and is enforced on every `to_state()` call via `assert_no_forbidden_fields` — this test exercises that pre-existing guarantee explicitly for D-008.
- Task 7 fix: the inline `from umbra_core.expression.presentation_state import RESULT_ACTIVITY_STATES` inside `test_rest_and_inactivity_are_valid_visible_states` moved to the top-level import block (no-inline-imports rule).
- Plan: docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md (Task 8 checklist)
- Mimir task: 8e126637c1c942b4ad688d6b3c3ee6b0 (Task 8 sub-task, closed); parent D-008 task cbbb61834c98463cb70fb9254ba08ea2 intentionally left open — controller owns lifecycle.

## Last validation
- Command: `pytest tests/test_d008.py -q` (55 passed) then `pytest tests/ -q` (365 passed, zero skips) — reproduced locally.
- `mimir_validation_run` rejected allowlisted `pytest -q` with "validation requires an active observed task" even after an intervening `mimir_task_observe` — same recurring precedent as Tasks 2-7. Validated locally instead.

## Open blockers
- `mimir_validation_run` remains blocked by "validation requires an active observed task" (recurring across Tasks 2-7 and now 8).
- Parent Mimir task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open (do not close per directive).
