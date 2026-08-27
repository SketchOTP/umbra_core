# CLOSE-02 evidence index

Permanent target: `/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02-final-authority-r1/`

The authority map and final contract were created before implementation. The
canonical target became unresponsive during the G1 freeze, so no claim is
made that a final evidence manifest or G1 result was written. The repository
closeout records the stop and the exact validation outputs.

- Focused structural/governance: `37 passed in 0.41s`
- Full path-safe suite: `885 passed, 7 failed, 2 skipped in 49.74s`
- D-012 short-path underlying failure: `OWNERSHIP_GENERATION_CONFLICT` on
  worker generation 3; same failure reproduced from the untouched baseline
- Baseline comparison: all seven full-suite failures matched the untouched
  `178f0e...` checkout
- G1: not launched (`run_count=0`)
