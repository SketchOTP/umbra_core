# CURRENT.md

## Active directive
- ID: D-20260724-0045-d009-task11-freeze
- Project directive: UMBRA-D-009
- Goal: Task 11 Stage B preregistration freeze
- Status: complete
- Freeze commit: `4e6c769f916fb7e8d0ca9ce42ddd0462c8654f3b`
- Next action: Task 12 complete minimum test list + prior seals

## Repo facts needed now
- Formal D-009 experiments must start from freeze commit `4e6c769f916fb7e8d0ca9ce42ddd0462c8654f3b`
- Preregistration: `experiments/d009/{thresholds,experiment-matrix,scenario-suite,habitat-definition,affordance-definitions,performance-protocol,seed-manifest}.json`

## Last validation
- Command: `pytest tests/test_d009.py::test_affordance_definitions_have_stable_hashes tests/test_d009.py::test_habitat_definitions_have_stable_hashes tests/test_d009.py::test_d009_profiles_add_manipulate_and_hold_fields -q`
- Result: 3 passed; post-commit hash verification script ALL_HASH_CHECKS_PASS

## Open blockers
- None
