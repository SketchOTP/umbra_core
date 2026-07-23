# CURRENT.md

## Active directive
- ID: D-20260723-1302-d008-task10-finding-individuality-summary-wiring
- Project directive: UMBRA-D-008
- Goal: Fix Important Task 10 finding — `individuality_summary` never populated on the live runtime path. Populate `ExpressionView.individuality_summary` in `Organism._push_expression_frame` from the organism's individuality engine / active habits / routines (copied snapshots only); add a regression test driving a real organism tick.
- Status: complete
- Acceptance: met — `Organism._individuality_summary()` populates disposition_vector/habit_active/routine_active from live D-007/D-005/D-006 state every tick; new regression test drives two real organisms and passes; full suite green (382 passed, 2 skipped — same pre-existing tkinter-display skips)
- Touched files: `umbra_core/runtime.py` (`Organism._individuality_summary()` + wiring into `_push_expression_frame`, `HABIT_CONFIDENCE_THRESHOLD` constant), `tests/test_d008.py` (+1 test, `IndividualityConfig`/`VerifiedEvidence` imports)
- Next action: Task 11 (per plan `docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md`) — parent D-008 Mimir task remains open, controller owns lifecycle

## Repo facts needed now
- `Organism._individuality_summary(last_outcome)` (new, `umbra_core/runtime.py`) builds the dict passed as `ExpressionView.individuality_summary` every tick: `disposition_vector` from `self.individuality.disposition_vector(scope)` where `scope = self._indiv_tags.get("learning_context", "default")` — the SAME scope `_finish_outcome` already writes verified evidence into. Reading a hardcoded `"default"` scope instead would silently return all-zero dispositions for every non-default `individuality_history` (H0 included, since H0 sets `learning_context="safe_explore"`), making the wiring a permanent no-op even though present — this was the actual root cause, not just "field never touched".
- `habit_active` = `self.memory.select_procedural(action=capability)` returns a skill with `confidence >= HABIT_CONFIDENCE_THRESHOLD` (0.45, matches the existing `tick_once` PROCEDURAL_KNOWLEDGE trust bar). `routine_active` = an `ACTIVE` entry in `self.social.routine_handles` whose `signal` equals this tick's verified `capability`. Both use `capability = last_outcome.capability if (last_outcome is not None and last_outcome.success) else None` — a denial or failed action never fabricates a habit/routine signal.
- All three summary values are plain copies: `disposition_vector()` already returns a fresh `dict[str,float]` (D-007), booleans are derived facts, not references — `ExpressionView`/`ExpressionEngine` still never hold a live reference into `IndividualityEngine`/`MemoryEngine`/`SocialEngine`.
- Regression test: `tests/test_d008.py::test_live_organism_populates_individuality_summary_via_push_expression_frame` — two real organisms (`individuality_enabled=True`, `expression_enabled=True`, `IndividualityConfig(modifiers_affect_arbitration=False)` to decouple arbitration from disposition so both pick the same action), one seeded with 75 `observe_verified` calls (public API) at the H0 `learning_context` scope, both ticked once, asserts `frame_ring[-1]` visible_condition_channels differ.
- Plan: `docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md` (Task 10 checklist + finding follow-up)
- Report: `.superpowers/sdd/task-10-report.md`
- Mimir task: `a8cc684b328f41ba8741d5e81b0c0255` (this fix, closed v3); parent D-008 task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open — controller owns lifecycle.

## Last validation
- Command: `pytest tests/test_d008.py -q` (72 passed, 2 skipped) then `pytest tests/ -q` (382 passed, 2 skipped) — reproduced locally.
- `mimir_validation_run` again rejected allowlisted `pytest -q` with "validation requires an active observed task" even after an intervening `mimir_task_observe` — same recurring precedent as Tasks 2-10.

## Open blockers
- `mimir_validation_run` remains blocked by "validation requires an active observed task" (recurring across Tasks 2-10 and this fix).
- This sandbox lacks `python3-tk`/a display — formal Tkinter soak (design §4 Gate 12 incremental cost) needs a machine/CI with real tkinter + display; not attempted here, not claimed.
- Parent Mimir task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open (do not close per directive).
