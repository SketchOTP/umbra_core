# CURRENT.md

## Active directive
- ID: D-20260724-0122-d009-task12-minimum-tests
- Project directive: UMBRA-D-009
- Goal: Task 12 complete minimum test list + prior seals
- Status: complete
- Freeze commit: `4e6c769f916fb7e8d0ca9ce42ddd0462c8654f3b`
- Next action: Task 13 experiment harness + raw evidence (Gates 1–12)

## Repo facts needed now
- Formal D-009 experiments must start from freeze commit `4e6c769f916fb7e8d0ca9ce42ddd0462c8654f3b`
- Preregistration: `experiments/d009/{thresholds,experiment-matrix,scenario-suite,habitat-definition,affordance-definitions,performance-protocol,seed-manifest}.json`
- `tests/test_d009.py`: 108 pytest items, 0 skips

## Last validation
- Command: `pytest tests/test_d009.py -q` → 108 passed; `pytest -q` → 513 passed, 2 skipped (Tkinter in test_d008 only)
- Result: Task 12 acceptance met

## Open blockers
- None
