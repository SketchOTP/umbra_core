# UMBRA-D-010 formal Gates 1–12 — interim (Task 13b)

**Status:** `failed_harness_defect` — **NOT QUALIFIED**

- **formal_execution_id:** `d010-fe-stage-b-v2`
- **freeze_commit:** `5d218d6fa1da8c49d2a6326037bbd10f3a457726`
- **agent_memory_directive:** `D-20260724-1544-d010-task13b-gates-v2`

## Per-gate summary

| Gate | Result |
|------|--------|
| 0 | PASS |
| 1 | PASS |
| 2 | FAIL (recurrence_learning_signal 0.0 vs threshold 0.55) |
| 3–12 | NOT_AGGREGATED (harness crash at gate 3 aggregation) |

## Root cause

Gate 3 `_aggregate_gate` pairs C0 `future_leakage_detection` against C2, but gate-critical matrix cells for gate 3 are C2/C7/C10 only. `values_a` length 1 vs `values_b` length 100 → `paired_length_mismatch`.

## Next

Freeze invalidate → patch harness aggregation (+ gate 2 metric investigation) → new Stage B freeze → new `formal_execution_id` → rerun Task 13b. Gate 13 performance deferred to Task 14.
