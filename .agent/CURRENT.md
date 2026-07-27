# CURRENT.md

## Active directive
- ID: D-20260727-0110-umbra-d012a1-real-runtime-dry-run-supervision
- Project directive: UMBRA-D-012A1
- Goal: Prove the frozen schedule operational through a supervised disposable real-runtime dry run.
- Status: complete — `UMBRA_D012A1_SUPERVISION_FAIL`; D-012A remains incomplete.
- Acceptance: Gates A-J; no P0 launch; evidence hashes; clean commit.
- Touched files: experiments/d012, tests/test_d012.py, docs/evidence/d012, governance.
- Next action: require a new authorized remediation directive for a distinct organism worker process, database ownership, crash cleanup, bounded separated logs, and the remaining checkpoint/refusal gates.

## Repo facts needed now
- Qualified release baseline: D-009; seal `af35371`; governance closeout `0880537`.
- D-010 is deferred: `UMBRA_D010_PERFORMANCE_FAIL`; it is not a D-011 prerequisite.

## Last validation
- Command: `python experiments/d012/validate_schedule.py`; `pytest -q tests/test_d012.py`; `pytest -q`; `python tools/validate_governance.py`; `git diff --check`.
- Result: schedule PASS; focused 8 passed; full suite FAIL (D-010 tick inventory: 1 failed, 665 passed, 2 skipped); governance PASS; diff check PASS. Disposable run completed 19 events, 4 restarts, 5 checkpoints, zero raw payloads, but used one OS process for supervisor and organism. No process remains.

## Open blockers
- Mimir V2 lifecycle tools (`mimir_project_resolve`, `mimir_task_begin`, and related tools) are unavailable in this session.
- Legacy Mimir failure outcome recorded successfully as `ep_4550657632244892` (not linked to a V2 retrieval session).
- D-012A1 failed supervisor authority/process gates and Gate J; D-012B and formal P0 remain unauthorized.
- No active D-012 process. Mimir V2 lifecycle remains unavailable.
