# CURRENT.md

## Active directive
- ID: D-20260727-1356-umbra-d012b-adaptive-fail-fast-p0
- Project directive: UMBRA-D-012B
- Goal: Execute one formal adaptive fail-fast P0 through the qualified distinct-worker supervisor.
- Status: in progress — adaptive P0 freeze and runner implemented; formal P0 not yet launched.
- Acceptance: Stop at first failed gate, clear pass after at least 20 active minutes, or inconclusive at 60 active minutes; preserve the required evidence; P1/P2 remain unlaunched; D-010 remains disabled and unchanged; clean process and worktree closeout.
- Touched files: experiments/d012, tests/test_d012_process_boundary.py, docs/evidence/d012, governance.
- Next action: commit the validated launch baseline, then execute exactly one formal P0.

## Repo facts needed now
- Qualified release baseline: D-009; seal `af35371`; governance closeout `0880537`.
- D-010 is deferred: `UMBRA_D010_PERFORMANCE_FAIL`; it is not a D-011 prerequisite.

## Last validation
- Command: `pytest -q tests/test_d012.py tests/test_d012_process_boundary.py`; schedule validator; governance validator; compile/diff/process checks.
- Result: 31 focused tests passed; adaptive 20–60 minute P0 configuration and governance validation passed; no D-012 process remains; formal P0 remains unlaunched.

## Open blockers
- Mimir V2 lifecycle tools (`mimir_project_resolve`, `mimir_task_begin`, and related tools) are unavailable in this session.
- Mimir project ID remains canonically bound as `7777645d52a91b49`; required V2 resolve/begin/context/validation/evidence/close calls cannot be performed or claimed.
- P1 and P2 are unauthorized. D-010 is deferred, disabled, excluded, and its frozen unrelated full-suite failure must not change.
