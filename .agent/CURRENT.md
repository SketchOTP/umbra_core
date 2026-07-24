# CURRENT.md

## Active directive
- ID: D-20260724-1607-d010-r1-rss-remediation
- Project directive: UMBRA-D-010-R1
- Goal: Diagnose Gate 13 RSS slope FAIL; remediate; new freeze; formal rerun; QUALIFIED only if earned
- Status: in_progress — diagnosis phase (no production patch yet)
- Starting tip: `acac8df`
- Failed freeze (preserved): `3178815` / `d010-fe-stage-b-v5`
- Outcome so far: `UMBRA_D010_PERFORMANCE_FAIL` (immutable)
- QUALIFIED: **not claimed**

## Acceptance
- Root cause classified A–E with evidence before patch
- Smallest fix; no threshold relaxation; failed evidence preserved
- New Stage B + formal_execution_id; Gates 1–12 + Gate 13 pass
- Zero-skip seal; parent Mimir closed only if QUALIFIED

## Touched files
- (diagnosis in progress)

## Next action
- Finish isolation diagnostics; gate A–E; then patch if resolved

## Repo facts needed now
- Parent Mimir: `9adf61b087ea4fa6a90a1c3bd401a9b3` (OPEN)
- Child task: `2cd88fa2924147278d04e96970a87d14` v1
- P0 soak DB: `.soak/d010_perf/soak_P0.sqlite` (~52 MiB; tick payload ~2.8 KiB dominated by TemporalAdvanceRecord)
- D-009 P0 soak ~22 MiB; no orchestration_tick_committed
- RSS jumps correlate with snapshot_every=200 and WAL_CHECKPOINT_EVERY_TICKS=500

## Last validation
- Command: soak DB static analysis
- Result: TemporalAdvanceRecord ~19.4 MiB of tick payloads; jumps @ 200/500 cadence

## Open blockers
- Production patch blocked until diagnosis gate A–E closed
