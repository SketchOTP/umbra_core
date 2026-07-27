# CURRENT.md

## Active directive
- ID: D-20260727-1133-umbra-d012a2-distinct-worker-closeout
- Project directive: UMBRA-D-012A2
- Goal: Replace in-process organism execution with a distinct OS worker and close only the direct supervision consequences.
- Status: complete — `UMBRA_D012A_FORMAL_SCHEDULE_FROZEN`; D-012B formal P0 only is authorized but unlaunched.
- Acceptance: Gates A-M; no formal P0; no D-010 changes; evidence hashes; review APPROVE; clean commit.
- Touched files: experiments/d012, tests/test_d012.py, docs/evidence/d012, governance.
- Next action: stop; a separate D-012B directive may create the formal execution and run only through the six-active-hour P0 checkpoint.

## Repo facts needed now
- Qualified release baseline: D-009; seal `af35371`; governance closeout `0880537`.
- D-010 is deferred: `UMBRA_D010_PERFORMANCE_FAIL`; it is not a D-011 prerequisite.

## Last validation
- Command: `pytest -q tests/test_d012.py tests/test_d012_process_boundary.py`; D-001–D-009 qualified regressions; D-011; full `pytest -q`; schedule/governance/hash/diff/protected/process checks.
- Result: D-012 28 passed; D-001–D-009 517 passed/2 expected skips; D-011 7 passed; full suite 685 passed/2 expected skips plus the sole frozen D-010 failure with identical 79-error SHA-256 `e531d099589f3127126205d6effe2e02e66418b5d7b254d7cd32cf3c72af6082`; all other checks PASS. Distinct-worker disposable run completed 19 events, 4 restarts, 5 checkpoints, zero raw payloads. Review APPROVE; no process remains.

## Open blockers
- Mimir V2 lifecycle tools (`mimir_project_resolve`, `mimir_task_begin`, and related tools) are unavailable in this session.
- Legacy Mimir failure outcome recorded successfully as `ep_4550657632244892` (not linked to a V2 retrieval session).
- Legacy Mimir D-012A2 qualified outcome recorded successfully as `ep_7ab406550fb04be5` (not linked to a V2 retrieval session).
- D-012A2 Gates A-M passed. D-012B formal P0 is authorized but not launched; P1/P2 remain unauthorized.
- No active D-012 process. Mimir V2 lifecycle remains unavailable.
