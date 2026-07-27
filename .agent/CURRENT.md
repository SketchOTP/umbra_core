# CURRENT.md

## Active directive
- ID: D-20260727-1224-umbra-d012b2-remediated-formal-p0
- Project directive: UMBRA-D-012B2
- Goal: Execute exactly one controlled remediated formal P0 under frozen Supplement S1.
- Status: in progress — pre-launch review `APPROVE`; Supplement S1 ready for freeze commit.
- Acceptance: read-only APPROVE; committed S1; one 20-60 active-minute fail-fast P0; required p0b2 evidence; Gates 0-10 adjudicated; original P0/B1 unchanged; clean closeout.
- Touched files: D-012 formal instrumentation, focused tests, Supplement S1/evidence, and governance only.
- Next action: validate and commit Supplement S1, confirm clean entry, then launch the one authorized formal execution.

## Repo facts needed now
- Qualified release baseline: D-009; seal `af35371`; governance closeout `0880537`.
- D-010 is deferred: `UMBRA_D010_PERFORMANCE_FAIL`; it is not a D-011 prerequisite.

## Last validation
- Command: `pytest -q tests/test_d012.py tests/test_d012_process_boundary.py tests/test_d001.py tests/test_d009.py tests/test_d011.py`; governance/schedule/diff checks.
- Result: 182 passed; governance PASS; frozen schedule PASS; diff check PASS; pre-launch review `APPROVE`.

## Open blockers
- Mimir V2 lifecycle tools (`mimir_project_resolve`, `mimir_task_begin`, and related tools) are unavailable in this session.
- Mimir project ID remains canonically bound as `7777645d52a91b49`; required V2 resolve/begin/context/validation/evidence/close calls cannot be performed or claimed.
- P1, P2, and D-012C are unauthorized. D-010 is deferred, disabled, excluded, and its frozen unrelated full-suite failure must not change.
- Exactly one formal P0 rerun is authorized; no additional remediation or rerun cycle is authorized.
