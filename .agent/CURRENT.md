# CURRENT.md

## Active directive
- ID: D-20260722-umbra-d007-lived-individuality
- Project directive: UMBRA-D-007
- Goal: Implement and validate lived individuality / history-shaped temperament
- Status: done — acceptance MET; UMBRA_D007_LIVED_INDIVIDUALITY_QUALIFIED
- Acceptance: MET — experiment gates pass; soak 7200.3s rss_p95 41.41 (<=180) slope 0.223 (<=1.0) cpu 0.0030 (<=0.05); 100k restart_continuity; zero-skip suite; evidence hashed; D-008 AUTHORIZED
- Touched files: umbra_core/individuality/, experiments/d007/, tests/test_d007.py, docs/evidence/d007/, umbra_core/{runtime,arbitration,events,embodiment}.py, .agent/*
- Next action: none — UMBRA-D-007 closed QUALIFIED; D-008 authorized when opened

## Repo facts needed now
- Ending/seal commit: 9589822
- Tip: cbd4391
- Soak: rss_p95 41.41 MiB, slope 0.223 MiB/h, cpu 0.0030 frac
- 100k: rss_p95 136.9 MiB, restart_continuity True

## Last validation
- Command: python experiments/d007/run_seal.py 9589822
- Result: UMBRA_D007_LIVED_INDIVIDUALITY_QUALIFIED

## Open blockers
- none
