# CURRENT.md

## Active directive
- ID: D-20260724-1947-d010-perf-fail-preserve-diagnose
- Project directive: UMBRA-D-010
- Goal: Preserve Gate 13 PERFORMANCE_FAIL; diagnose shared RSS slope (no source edit)
- Status: diagnosis recorded — awaiting root-cause confirmation before invalidate
- Freeze tip: `3178815` / `d010-fe-stage-b-v5` (still current; **not** invalidated yet)
- Outcome: `UMBRA_D010_PERFORMANCE_FAIL`
- QUALIFIED: **not claimed**

## Gate 13 campaign (preserved)
- 100k/lifecycle: PASS
- P0/P1/P2: all FAIL — `sustained_segment_growth`; slopes ~1.9–2.1 > 1.0; RSS p95 OK
- P2 distinguishes Tkinter: **+~9 MiB level**, same growth family (not Tk-specific)
- Common signal: SQLite `database_growth_mib` ≈ **39 MiB** all modes; stepwise RSS jumps ~100s then ~500s
- Artifacts: `formal-performance-outcome.json`, `gate13-rss-diagnosis.md`

## Note on seal
- Task 14 agent ran seal and wrote `final-verdict.md` = `UMBRA_D010_PERFORMANCE_FAIL` (no QUALIFIED). Operator asked not to seal; treat as FAIL record only.

## Next (do not skip)
1. Deepen diagnosis (tracemalloc/smaps + sqlite accounting) if needed
2. Patch + test → review → **new Stage B** + new `formal_execution_id` → rerun Gate 13

## Locked
- Parent Mimir: `9adf61b087ea4fa6a90a1c3bd401a9b3` (OPEN)
- Diagnose subtask: `70cba7b7829240d39216d87e561c09e3`

## Open blockers
- Gate 13 FAIL blocks QUALIFIED; root cause not yet patched
