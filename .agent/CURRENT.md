# CURRENT.md

## Active directive
- ID: D-20260721-umbra-d002p-performance-remediation
- Project directive: UMBRA-D-002P
- Goal: Remediate D-002 runtime memory growth; RUNTIME_READY-anchored 2h VmRSS revalidation
- Status: in_progress — remediation committed; soak pending
- Acceptance: Gates 0–5; D-002V remains PERFORMANCE_FAIL; slope ≤1 MiB/h from RUNTIME_READY
- Touched files: umbra_core/{util,events,runtime,persistence,self_model}, tests/test_d002p.py, experiments/d002p/, docs/evidence/d002p/, .agent/*
- Next action: 2h soak from remediation commit; seal evidence

## Repo facts needed now
- Starting tip: 97e5df2175817b9122f5724aaedd2c320d12510c
- D-002V verdict preserved: UMBRA_D002V_PERFORMANCE_FAIL
- Mimir task: 8e2d40832317467c8eee34ab873e6234
- Remediations: BoundedRing prefill, RUNTIME_READY, snapshot prune, drop duplicate metrics.prediction_errors

## Last validation
- Command: pytest tests/ → 99 passed, 0 skipped
- Result: green pre-soak

## Open blockers
- 2h soak not yet run
