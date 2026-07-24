# CURRENT.md

## Active directive
- ID: D-20260724-1607-d010-r1-rss-remediation
- Project directive: UMBRA-D-010-R1
- Goal: Remediate Gate 13 RSS; new Stage B v6; formal rerun; QUALIFIED only if earned
- Status: in_progress — freeze v6 ready; formal Gates 1–12 + Gate 13 rerun next
- Starting tip: `acac8df`
- Remediation commit: `bab1fcd`
- New Stage B freeze: `f3883ba` / `d010-fe-stage-b-v6`
- Failed freeze preserved: `3178815` / `d010-fe-stage-b-v5` + `UMBRA_D010_PERFORMANCE_FAIL`
- QUALIFIED: **not claimed**

## Root cause (A)
- `TemporalEngine._committed_advance_ids` unbounded per tick
- Fix: keep latest id only; observation-plan set same; POST_HOC clear on commit
- Secondary: `_release_native_arenas` after snapshot/WAL

## Acceptance
- P0/P1 ≤ 1.0 MiB/h; Gates 1–12 pass on v6; zero-skip seal; clean worktree

## Next action
- Rerun Gates 1–12 under v6 → independent review → Gate 13 → seal

## Locked
- Parent Mimir: `9adf61b087ea4fa6a90a1c3bd401a9b3` (OPEN)
- Child: `2cd88fa2924147278d04e96970a87d14`

## Open blockers
- Formal campaign not yet complete under v6
