# UMBRA-D-010 Gate 13 Performance Outcome

**Outcome:** `UMBRA_D010_PERFORMANCE_FAIL`

**Freeze tip:** `317881537f0991914949d92659231ba79d52aec1` (`d010-fe-stage-b-v5`)
**Software commit at run:** `a1342ee1b6ad16e66c8475b374e6366f9db13675`
**Task 13e Gates 1-12 evidence:** `a1342ee` (PASS; preserved)

## Mode results (Supplement S3)

| Mode | Pass | RSS p95 (MiB) | Slope (MiB/h) | Extension reason |
|------|------|---------------|---------------|------------------|
| P0 | FAIL | 45.05859375 | 1.9034090909090908 | `inconclusive_after_max:sustained_segment_growth` |
| P1 | FAIL | 45.2265625 | 1.913861146907216 | `inconclusive_after_max:sustained_segment_growth` |
| P2 | FAIL | 54.4140625 | 2.077702702702703 | `inconclusive_after_max:sustained_segment_growth` |

100k: PASS · Lifecycle: PASS · Seal: **not run** · QUALIFIED: **not claimed**

Failed frozen campaign preserved for diagnosis. Source changes require Stage B invalidate + new formal_execution_id + Gate 13 rerun.
