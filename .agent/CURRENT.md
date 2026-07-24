# CURRENT.md

## Active directive
- ID: D-20260724-task14-d009-perf-seal
- Project directive: UMBRA-D-009
- Goal: Task 14 adaptive P0/P1/P2 performance + final seal
- Status: harness committed; full S3 matrix running
- Acceptance: Gate 13 pass; seal QUALIFIED if earned; parent Mimir closed on seal commit; clean worktree
- Touched files: experiments/d009/{run_performance,run_seal,with_tk_display}.sh
- Next action: Run full 100k+P0/P1/P2; seal; commit evidence; close parent Mimir

## Repo facts needed now
- Freeze: `4e6c769`
- Task 13 complete: `UMBRA_D009_TASK13_GATES_1_12_PASS` at `3657420`
- Parent Mimir `06b5b59709864e11bddb8c1da56dd66e` OPEN until seal
- Sub-task Mimir: `d52577c3dfca4bbfaf774e62b662cb51`

## Last validation
- Command: D009_PERF_SMOKE=1 — 100k, lifecycle, P0, P2 all pass
- Result: harness smoke OK

## Open blockers
- Full adaptive soak wall-clock (~3h) in progress
