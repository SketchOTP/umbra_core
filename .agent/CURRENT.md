# CURRENT.md

## Active directive
- ID: D-20260722-1439-d006-task12-experiment-harness
- Project directive: UMBRA-D-006
- Goal: Task 12 — paired-seed experiment harness over frozen matrix/thresholds; generate docs/evidence/d006/*.json asserting gates 1-9 numerically (performance deferred to Task 13)
- Status: done
- Acceptance: MET — frozen thresholds/matrix unmodified; 100 paired seeds/gate-critical cell; all required result files written; gates 1-9 numeric all PASS; C3 leak fails closed; results committed
- Touched files: experiments/d006/run_experiment.py, experiments/d006/run_closeout.py, docs/evidence/d006/*.json, .superpowers/sdd/task-12-report.md, .agent/*
- Next action: Task 13 — performance soak (Gate 12), unskip test_performance_soak_within_bounds, final UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED seal

## Repo facts needed now
- Mimir project: 7777645d52a91b49; Task 12 mimir_task 80a390a43e204d6c806f57a8c61226ae (begun/observed/closed)
- Harness drives SocialEngine directly with synthetic cues + frozen response_policy_for_history (embodiment cue salt < perception noise); paired seeds vary partner-response RNG
- Gate 2 = two-partner separation probe (C0=0.595, C2=0.0, C4=0.217); Gate 6 viability = survival-critical excursions only (stimulation benign)
- All 12 evidence files under docs/evidence/d006/; interim verdict UMBRA_D006_EXPERIMENT_GATES_1_9_PASS; Gate 12 perf deferred to Task 13

## Last validation
- Command: python experiments/d006/run_experiment.py ; python experiments/d006/run_closeout.py
- Result: gates 1-9 all pass (1875 rows, 12.7s); closeout UMBRA_D006_EXPERIMENT_GATES_1_9_PASS; pytest tests/test_d006.py 77 passed/1 skipped (Gate 12 by design)

## Open blockers
- mimir_validation_run: "validation requires an active observed task" (same precedent Tasks 4-11) — validated locally; task begun/observed/closed honestly
