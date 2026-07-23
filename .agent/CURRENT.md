# CURRENT.md

## Active directive
- ID: D-20260723-1902-d008-task14-adaptive-soak-s3
- Project directive: UMBRA-D-008
- Goal: Task 14 Gate 12 under Supplement S3 + seal QUALIFIED
- Status: in_progress — harness ready; full ~105min adaptive soak starting
- Acceptance: 100k + P0/P1/P2 S3 soak + lifecycle + zero-skip + QUALIFIED
- Touched files: experiments/d008/run_{performance,seal}.py, performance-protocol.json, design S3, tests/test_d008.py
- Next action: Full performance matrix → seal → close parent Mimir

## Repo facts needed now
- Task 13: UMBRA_D008_TASK13_GATES_1_11_PASS (de9fc10)
- S3: warmup 300s + 1800s measure; max 3600s/mode; no fixed 2h
- Tk: user-local umbratk extract + Xvfb :99 (system python3-tk absent)
- Parent Mimir: cbbb61834c98463cb70fb9254ba08ea2
- Task Mimir: 6f0856d4105e499b8d8c47b76e8219ac

## Last validation
- Command: pytest tests/test_d008.py -q (with DISPLAY=:99)
- Result: 97 passed

## Open blockers
- Full S3 soak wall-clock (~105 min + extensions if needed)
