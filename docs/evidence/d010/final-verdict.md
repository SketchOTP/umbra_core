# UMBRA-D-010 Final Verdict

**Verdict:** `UMBRA_D010_PERFORMANCE_FAIL`

**Ending commit:** `aee03e7`
**Mimir project:** `7777645d52a91b49`
**Adaptive soak:** Supplement **S3** (authorized replacement for fixed two-hour soak)

## Gate summary

| Check | Result |
|-------|--------|
| Task 13 Gates 1–12 | `PASS` |
| Gate 13 performance (S3 adaptive) | `FAIL` |
| Prior seals D-001 + D-009 | `PASS` |
| Zero-skip test suite | `PASS` (passed=126, skipped=0) |

## Evidence surfaces

| Surface | Present |
|---------|---------|
| formal-run-outcome.json | `yes` |
| experiment-summary.json | `yes` |
| performance-results.json | `yes` |

D-010 Task 14 uses authorized adaptive-soak Supplement S3. Absolute and incremental
RSS/CPU limits from `experiments/d010/thresholds.json` remain binding.

D-009 `UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED` prerequisite required.
