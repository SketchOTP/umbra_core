# CURRENT.md

## Active directive
- ID: D-20260724-1947-d010-perf-fail-preserve-diagnose
- Project directive: UMBRA-D-010
- Goal: Gate 13 PERFORMANCE_FAIL preserved; diagnosis done; await invalidate/patch authorization
- Status: **independent review Approve** (honest FAIL package) — parent Mimir OPEN
- Freeze tip: `3178815` / `d010-fe-stage-b-v5` (**not** invalidated yet)
- Master tip: `be23da6`
- Outcome: `UMBRA_D010_PERFORMANCE_FAIL`
- QUALIFIED: **not claimed**

## Gate 13 (preserved)
- P0/P1/P2 FAIL (`sustained_segment_growth`, slopes ~1.9–2.1)
- 100k + lifecycle PASS
- Common-path: SQLite ~39 MiB growth; stepwise RSS; not Tkinter-driven
- Diagnosis: `docs/evidence/d010/gate13-rss-diagnosis.md`

## Reviews
- Task 14 FAIL package: Approve ([Review D-010 Task 14 FAIL](8268b3b1-7549-4d04-96c2-b3235478d6bb))
- Task 14 implementer: [Run D-010 Task 14 perf seal](c50f8db9-cea9-4847-8eb4-d94427d64118)

## Next
```text
deepen diagnosis if needed
→ patch + test
→ independent review
→ new Stage B + formal_execution_id
→ rerun Gate 13
```
Do **not** close parent Mimir until QUALIFIED seal tip (or explicit operator close).

## Locked
- Parent Mimir: `9adf61b087ea4fa6a90a1c3bd401a9b3` (OPEN)

## Open blockers
- Gate 13 FAIL blocks QUALIFIED; no source patch until invalidate path authorized
