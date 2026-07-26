# CURRENT.md

## Active directive
- ID: D-20260727-0035-umbra-d012-integrated-continuous-life
- Project directive: UMBRA-D-012
- Goal: Qualify one integrated organism over a 72-active-hour continuous-life history.
- Status: in_progress — entry audit complete; protocol design/freeze pending; D-010 disabled; no real devices.
- Acceptance: Gates 0-15; one continuous history reaches 72 active hours; prior seals unchanged; independent review approves; clean closeout.
- Touched files: experiments/d012, tests/test_d012.py, evidence, governance; production only for proven integration defects.
- Next action: define and freeze the complete opportunity, intervention, checkpoint, restart, body-transfer, and corruption schedules before launching P0-P2.

## Repo facts needed now
- Qualified release baseline: D-009; seal `af35371`; governance closeout `0880537`.
- D-010 is deferred: `UMBRA_D010_PERFORMANCE_FAIL`; it is not a D-011 prerequisite.

## Last validation
- Command: `pytest -q`; `python tools/validate_governance.py`; D-011 100k stress.
- Result: D-011C closeout passed; D-012 validation pending.

## Open blockers
- Mimir V2 lifecycle tools (`mimir_project_resolve`, `mimir_task_begin`, and related tools) are unavailable in this session.
- No active D-012 process. Mimir V2 lifecycle remains unavailable.
