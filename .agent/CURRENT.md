# CURRENT.md

## Active directive
- ID: D-20260726-2301-umbra-g001c-worktree-reconciliation
- Project directive: UMBRA-G-001C (parent UMBRA-G-001)
- Goal: Classify and safely resolve the pre-existing worktree without changing scientific conclusions.
- Status: complete — `UMBRA_G001_GOAL_AUTHORITY_RESTORED`; G-001 governance and D-010 diagnostic work committed separately.
- Acceptance: every path classified; G-001 and D-010 diagnostic changes separate; validator/tests/diff check pass; clean worktree.
- Touched files: classification ledger, closeout records, append-only governance files; existing G-001/D-010 paths only as classified.
- Next action: stop. Operator may separately decide Option A or B.

## Repo facts needed now
- Qualified release baseline: D-009; seal `af35371`; governance baseline `bb90e61`.
- D-010 verdict: `UMBRA_D010_PERFORMANCE_FAIL`; Gates 0–12 PASS; Gate 13 FAIL; Stage B v7 NOT CREATED.
- Parent Mimir: `9adf61b087ea4fa6a90a1c3bd401a9b3` OPEN.

## Last validation
- Command: `python tools/validate_governance.py && pytest -q && git diff --check`.
- Result: validator passed; 651 passed, 2 documented expected skips; `git diff --check` passed.

## Open blockers
- Mimir V2 lifecycle tools (`mimir_project_resolve`, `mimir_task_begin`, and related tools) are unavailable in this session.
