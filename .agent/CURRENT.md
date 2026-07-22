# CURRENT.md

## Active directive
- ID: D-20260722-1430-d006-task11-test-suite-completion
- Project directive: UMBRA-D-006
- Goal: Task 11 — complete tests/test_d006.py directive+design minimum test suite
- Status: done
- Acceptance: met — 7 tests added (satiation decline, absence non-escalation/non-frequency/non-viability-damage/non-punishment, different-histories behavior, Gate 12 explicitly-skipped pre-soak placeholder); all design §8 minimum-test-list names present; full suite green
- Touched files: tests/test_d006.py, .superpowers/sdd/task-11-report.md, .agent/*
- Next action: Task 12 (soak) / Task 13 (unskip Gate 12 with evidence)

## Repo facts needed now
- Mimir project: 7777645d52a91b49
- Mimir task: 7609c47c63604e22a6d1fe60c909ed52
- H0 and H7 both show an identical brief `stimulation` critical dip (~tick 44-45) with `social_enabled=True` — pre-existing, unrelated to absence; absence-viability test diffs H7 trace against H0 baseline instead of asserting zero criticals
- `_build_reliability()` test helper defaults `contingent=3` even when only `none=` is passed — pass `contingent=0` explicitly for a pure-NONE history
- Gate 12 (100k-tick/2h soak) test added as `pytest.mark.skip` with named reason; final sealed suite still requires zero skips (Task 13 supplies evidence)

## Last validation
- Command: pytest tests/test_d006.py -v && pytest tests/ -q
- Result: 77 passed/1 skipped (test_d006.py); 255 passed/1 skipped (full suite)

## Open blockers
- mimir_validation_run: "validation requires an active observed task" (same precedent as Tasks 4–10); mimir_task_close succeeded with locally-verified test results
