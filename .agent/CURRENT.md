# CURRENT.md

## Active directive
- ID: D-20260727-0005-umbra-d011c-perception-qualification
- Project directive: UMBRA-D-011C
- Goal: Qualify the existing governed synthetic perception-adapter boundary without redesign.
- Status: closed qualified — `UMBRA_D011_GOVERNED_PERCEPTION_ADAPTERS_QUALIFIED`; no device drivers.
- Acceptance: Met: C0-C8 controls, real ledger replay, two frozen 100k runs, evidence hashes, read-only APPROVE review, and closeout checks. D-009 predecessor preserved; D-010 unused.
- Touched files: D-011 contracts, membrane/event/replay integrity, experiments, evidence, governance.
- Next action: Stop. D-012 is authorized by status but was not started.

## Repo facts needed now
- Qualified release baseline: D-009; seal `af35371`; governance closeout `0880537`.
- D-010 is deferred: `UMBRA_D010_PERFORMANCE_FAIL`; it is not a D-011 prerequisite.

## Last validation
- Command: `pytest -q`; `python tools/validate_governance.py`; D-011 100k stress.
- Result: `pytest -q`, governance validation, diff check, protected-artifact check, no D-011 processes, and read-only review passed.

## Open blockers
- Mimir V2 lifecycle tools (`mimir_project_resolve`, `mimir_task_begin`, and related tools) are unavailable in this session.
