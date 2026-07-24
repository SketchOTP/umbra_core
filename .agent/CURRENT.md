# CURRENT.md

## Active directive
- ID: D-20260723-2307-d009-task1-habitat-state
- Project directive: UMBRA-D-009
- Goal: Task 1 — Habitat state model + hashing + object versioning
- Status: completing — tests green, committing
- Acceptance: 3 named tests GREEN; full suite green; commit; task-1-report.md
- Touched files: `umbra_core/habitat/`, `tests/test_d009.py`
- Next action: Task 2 — HabitatEngine sole writer + projection

## Repo facts needed now
- Parent Mimir task: `06b5b59709864e11bddb8c1da56dd66e` (open — do not close)
- Task 1 Mimir subtask: `7bbf7637ef7a496cbebf8e1911b8bdd2`
- Design: `79a00f2` + A1–A6 on `da60f20`
- Frozen habitat definition hash (sample fixture): `495efd05b8bc8bba8a20d8319f273be772d1b7f70ff0913aa4a455c5b97420c6`

## Last validation
- Command: `pytest tests/test_d009.py -q` + `pytest tests/ -q`
- Result: 3 passed (d009); 408 passed, 2 skipped (full)

## Open blockers
- None
