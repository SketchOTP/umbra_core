# CURRENT.md

## Active directive
- ID: D-20260721-umbra-d002p-performance-remediation
- Project directive: UMBRA-D-002P
- Goal: Remediate D-002 runtime memory growth; RUNTIME_READY-anchored 2h VmRSS revalidation
- Status: done — UMBRA_D002P_PERFORMANCE_REMEDIATION_QUALIFIED
- Acceptance: Gates 0–5 met; D-002V FAIL preserved; slope 0.217 ≤ 1.0
- Touched files: umbra_core/*, tests/test_d002p.py, experiments/d002p/, docs/evidence/d002p/, .agent/*
- Next action: D-003 authorized when opened

## Repo facts needed now
- Starting tip: 97e5df2175817b9122f5724aaedd2c320d12510c
- Soak commit: 13bdce2311b2a9571d2efcf1a6500a91760bb171
- D-002V preserved: UMBRA_D002V_PERFORMANCE_FAIL
- D-002P verdict: UMBRA_D002P_PERFORMANCE_REMEDIATION_QUALIFIED
- Mimir task: 8e2d40832317467c8eee34ab873e6234
- D-003 AUTHORIZED: YES

## Last validation
- Command: pytest tests/; 2h RUNTIME_READY VmRSS soak
- Result: 99 passed 0 skipped; slope 0.217; gate_performance_pass=true

## Open blockers
- none for D-002P
