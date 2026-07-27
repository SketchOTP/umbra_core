# CURRENT.md

## Active directive
- ID: D-20260727-0035-umbra-d012-integrated-continuous-life
- Project directive: UMBRA-D-012
- Goal: Qualify one integrated organism over a 72-active-hour continuous-life history.
- Status: in_progress — D-012A structural schedule is incomplete; D-010 disabled; no real devices.
- Acceptance: Gates 0-15; one continuous history reaches 72 active hours; prior seals unchanged; independent review approves; clean closeout.
- Touched files: experiments/d012, docs/evidence/d012, governance; production only for proven integration defects.
- Next action: implement disposable real-runtime dry run and checkpoint supervision, then rerun D-012A freeze gates before authorizing P0.

## Repo facts needed now
- Qualified release baseline: D-009; seal `af35371`; governance closeout `0880537`.
- D-010 is deferred: `UMBRA_D010_PERFORMANCE_FAIL`; it is not a D-011 prerequisite.

## Last validation
- Command: `pytest -q`; `python tools/validate_governance.py`; D-011 100k stress.
- Result: D-012A structural schedule validator passed; real dry run not run, so P0 remains unauthorized.

## Open blockers
- Mimir V2 lifecycle tools (`mimir_project_resolve`, `mimir_task_begin`, and related tools) are unavailable in this session.
- No active D-012 process. Mimir V2 lifecycle remains unavailable.
