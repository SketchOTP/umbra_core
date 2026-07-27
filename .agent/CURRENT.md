# CURRENT.md

## Active directive
- ID: D-20260727-1224-umbra-d012b2-remediated-formal-p0
- Project directive: UMBRA-D-012B2
- Goal: Execute exactly one controlled remediated formal P0 under frozen Supplement S1.
- Status: complete — `UMBRA_D012B_P0_INTEGRITY_FAIL`.
- Acceptance: read-only APPROVE; committed S1; one 20-60 active-minute fail-fast P0; required p0b2 evidence; Gates 0-10 adjudicated; original P0/B1 unchanged; clean closeout.
- Touched files: D-012 formal instrumentation, focused tests, Supplement S1/evidence, and governance only.
- Next action: stop; another formal P0, remediation, P1, P2, and D-012C are unauthorized.

## Repo facts needed now
- Qualified release baseline: D-009; seal `af35371`; governance closeout `0880537`.
- D-010 is deferred: `UMBRA_D010_PERFORMANCE_FAIL`; it is not a D-011 prerequisite.

## Last validation
- Command: formal execution; full and focused regressions; governance/schedule/diff/freeze/hash/process checks.
- Result: formal fail-fast at tick 181 energy 0.0485; 182 focused passed; full 691 passed plus sole frozen D-010 failure (79-error fingerprint `e531d099...af6082`); chain 731 valid; cleanup and 16 evidence hashes PASS.

## Open blockers
- Mimir V2 lifecycle tools (`mimir_project_resolve`, `mimir_task_begin`, and related tools) are unavailable in this session.
- Mimir project ID remains canonically bound as `7777645d52a91b49`; required V2 resolve/begin/context/validation/evidence/close calls cannot be performed or claimed.
- P1, P2, and D-012C are unauthorized. D-010 is deferred, disabled, excluded, and its frozen unrelated full-suite failure must not change.
- The one authorized formal P0 rerun has been consumed. No additional remediation or rerun cycle is authorized.
