# CURRENT.md

## Active directive
- ID: D-20260723-umbra-d009-persistent-habitat-agency
- Project directive: UMBRA-D-009
- Goal: Implement persistent digital habitat + governed environmental agency per approved design
- Status: Task 1 complete — Task 2 next (HabitatEngine sole writer + projection)
- Acceptance: Tasks 0–14 complete; QUALIFIED or allowed fail verdict; Mimir closed; clean worktree
- Touched files: `umbra_core/habitat/state.py`, `tests/test_d009.py`
- Next action: Task 2 — HabitatEngine + projection + queries

## Repo facts needed now
- Task 1 commit: `3b44c18`
- Parent Mimir task: `06b5b59709864e11bddb8c1da56dd66e` (open)
- Sample habitat definition hash: `495efd05b8bc8bba8a20d8319f273be772d1b7f70ff0913aa4a455c5b97420c6`

## Last validation
- Command: `pytest tests/test_d009.py -q` + `pytest tests/ -q`
- Result: 3 passed (d009); 408 passed, 2 skipped (full)

## Open blockers
- None
