# CURRENT.md

## Active directive
- ID: D-20260723-1405-d008-task12-minimum-tests
- Project directive: UMBRA-D-008
- Goal: Cross-check directive §16 minimum test names against `tests/test_d008.py`; add the 5 missing brief-named tests (`test_d001_through_d007_seals_unchanged`, `test_prior_behavior_regressions_within_bounds`, `test_no_deferred_modules`, `test_100k_tick_boundedness`, `test_two_hour_visible_runtime_soak`).
- Status: complete
- Acceptance: met — all 5 named tests added and pass; every other directive-named test from Tasks 1-11 was already present; no `pytest.mark.skip` added for Gate 12 (used D-007's no-skip artifact-reading pattern per brief preference, not D-006's interim-skip pattern); full suite green (405 passed, 2 skipped — same pre-existing tkinter-display skips)
- Touched files: `tests/test_d008.py`
- Next action: Task 13 (formal experiment matrix, per plan) — NOT started here per brief scope limit. Task 14 (100k+2h soak+seal) also not started. Parent D-008 Mimir task remains open, controller owns lifecycle.

## Repo facts needed now
- `tests/test_d008.py` now has 95 tests (was 90) + 2 pre-existing tkinter-skips. New tests appended after the Task-11 C8 tests, under a new `# ----- Task 12: directive §16 minimum-list cross-check + prior seals -----` section.
- `test_d001_through_d007_seals_unchanged` validates `docs/evidence/{d001,d002p,d003,d004,d005,d006,d007}/evidence-hashes.json` against live file hashes + the D-007 final-verdict string — same shape as D-007's own `test_d001_through_d006_seals_unchanged`, one directive further.
- `test_prior_behavior_regressions_within_bounds` smoke-checks `DevelopmentEngine`, `WorldModel`, `MemoryEngine`, `SelfModel`, `SocialEngine` (via `condition_to_social_config`), and `IndividualityEngine` are all still importable/functional — mirrors D-007's `test_prior_regressions_remain_within_bounds` but covers one more prior engine (individuality, since D-008 sits directly atop D-007).
- `test_no_deferred_modules` asserts `umbra_core/{language,mood,emotion,personality,llm,chemistry,protocell,robotics,camera,microphone}` do not exist, and that no production or test body profile (incl. `CONSTRAINED_TEST_BODY`) exposes invented `MAINTAIN`/`PRACTICE` capabilities — directly enforces the directive Forbidden list, same style as D-004/D-005/D-006's `test_no_deferred_modules_added`.
- Gate 12 (`test_100k_tick_boundedness`, `test_two_hour_visible_runtime_soak`): chose D-007's later no-skip pattern over D-006's Task-12-stage `pytest.mark.skip` pattern, per the brief's explicit preference for "artifact-reading tests if evidence not yet present." `test_100k_tick_boundedness` runs a 2000-tick accelerated proxy and asserts frame-ring/habitat/source-ref bounds from `experiments/d008/thresholds.json`; the full 100k+real-soak run is deferred to Task 14's `experiments/d008/run_performance.py` (not built yet). `test_two_hour_visible_runtime_soak` always asserts the threshold contract (`soak_seconds_min>=7200`, `rss_p95_mib_max==180`) and additionally validates `soak`/`ui_incremental` sub-objects only if `docs/evidence/d008/performance-results.json` already exists (it does not yet — Task 14 will write it).
- Supplement S2 (trusted-caller poll) is already fully implemented and tested (Task 11's Gate 8 fix, `test_reference_renderer_protocol_has_no_ring_channel` / `test_hostile_renderer_write_attempts_are_rejected`) — confirmed via design doc read, no new S2-specific test needed for this task.
- Plan: `docs/superpowers/plans/2026-07-23-umbra-d008-coherent-digital-embodiment.md` (Task 12 checklist)
- Report: `.superpowers/sdd/task-12-report.md` (this task's report; note a stale D-006-era `task-12-report.md`/`task-12-review.md` existed at the same numeric path from a prior directive cycle — overwritten with this D-008 Task 12 report; `.superpowers/sdd/` is gitignored)
- Mimir task: `7a39ada9ec1e4fad8459db4552830fba` (this task, closed v3); parent D-008 task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open — controller owns lifecycle.

## Last validation
- Command: `pytest tests/test_d008.py -q` (95 passed, 2 skipped) then `pytest -q` full suite (405 passed, 2 skipped) — reproduced locally.
- `mimir_validation_run(pytest -q)` again rejected with "validation requires an active observed task" — same recurring precedent as Tasks 2-11 and both Gate 8 fixes.

## Open blockers
- `mimir_validation_run` remains blocked by "validation requires an active observed task" (recurring across Tasks 2-11 and this task).
- Task 13 (formal experiment matrix) and Task 14 (100k+2h soak+seal) not started — explicitly out of scope for this task per brief.
- Parent Mimir task `cbbb61834c98463cb70fb9254ba08ea2` intentionally left open (do not close per directive).
