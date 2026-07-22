# CURRENT.md

## Active directive
- ID: D-20260722-1532-d006-task12-critical-fix
- Project directive: UMBRA-D-006
- Goal: Fix Task 12 Critical — organism-level partner recognition collapsed distinct partners (PartnerTrueCues separation ~0.17 < PerceptionMembrane identity-cue noise ~0.33); make distinct partners separable through the real path without editing frozen thresholds
- Status: done — acceptance MET
- Acceptance: MET — organism real path forms 2 distinct H8 hypotheses + swap detection (no silent merge) and H9 ambiguous stays merged, across 20 seeds (1.0/0.0/1.0); gates 1-9 re-run PASS incl organism-level gate3; frozen recognition_match_threshold(0.55)/thresholds.json/matrix unchanged
- Touched files: umbra_core/embodiment.py, umbra_core/perception.py, experiments/d006/{run_experiment,run_closeout}.py, tests/test_d006.py, docs/evidence/d006/* (regenerated), .superpowers/sdd/task-12-report.md, .agent/*
- Next action: Task 13 (performance soak + final UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED seal); Critical finding resolved

## Repo facts needed now
- Root cause: identity separation lived in a small scalar salt below perception noise. Fix keeps noise but (a) antipodal per-index identity basis in PartnerTrueCues.for_history (noise-free inter-partner cue distance ~0.69), (b) PerceptionMembrane identity-signature noise floor 0.14 < spatial noise 0.33 (cues stay noisy). Ambiguous H9 keeps tiny amplitude so partners collapse/contest.
- Gate 3 now requires BOTH synthetic mechanism check AND organism real-path check (_organism_recognition, 20 seeds). Two end-to-end organism tests added.
- Frozen thresholds.json / experiment-matrix.json untouched (fix was in production cue/perception calibration + harness, not frozen gates).

## Last validation
- Command: python -m pytest tests/test_d006.py -q ; python experiments/d006/run_experiment.py ; python experiments/d006/run_closeout.py
- Result: 79 passed/1 skipped; gates 1-9 PASS (1875 rows, 64.7s); UMBRA_D006_EXPERIMENT_GATES_1_9_PASS

## Open blockers
- mimir_validation_run: "validation requires an active observed task" (same precedent Tasks 4-12) — validated locally; Mimir task begun/observed/closed
