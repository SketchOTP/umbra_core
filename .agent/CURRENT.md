# CURRENT.md

## Active directive
- ID: D-20260724-1544-d010-task13b-gates-v2
- Project directive: UMBRA-D-010
- Goal: Task 13b — formal Gates 1–12 evidence under Stage B freeze v2
- Status: ended — failed_harness_defect (aggregation gate 3)
- Freeze tip: `5d218d6fa1da8c49d2a6326037bbd10f3a457726`
- formal_execution_id: `d010-fe-stage-b-v2`
- Next action: freeze invalidate gate 3 aggregation (+ gate 2 metric review) → new Stage B → rerun Task 13b

## Locked
- Parent Mimir: `9adf61b087ea4fa6a90a1c3bd401a9b3` (OPEN until seal)
- Constraint: evidence commits only; no source edits under freeze tip

## Last validation
- Command: `python experiments/d010/validate_evidence.py`
- Result: FAIL (missing gates 3–12 summaries; partial gate files)

## Open blockers
- Harness gate 3 aggregation defect (`paired_length_mismatch:g3_future_leakage_zero:1!=100`)
- Gate 2 recurrence_learning_signal 0.0 (investigate after harness fix)
