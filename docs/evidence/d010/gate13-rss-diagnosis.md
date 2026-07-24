# Gate 13 RSS diagnosis (read-only) — UMBRA-D-010

**Directive:** `D-20260724-1947-d010-perf-fail-preserve-diagnose`  
**Freeze:** `3178815` / `d010-fe-stage-b-v5`  
**Outcome:** `UMBRA_D010_PERFORMANCE_FAIL`  
**Source edits:** none (investigation only)

## Campaign summary

| Mode | Pass | RSS p95 | Reported slope | DB growth | Failure reason |
|------|------|---------|----------------|-----------|----------------|
| P0 | FAIL | 45.1 | 1.90 MiB/h | 38.9 MiB | `inconclusive_after_max:sustained_segment_growth` |
| P1 | FAIL | 45.2 | 1.91 MiB/h | 39.1 MiB | same |
| P2 | FAIL | 54.4 | 2.08 MiB/h | 38.8 MiB | same |

Threshold: `rss_slope_mib_per_hour_max = 1.0`. Absolute RSS p95 cap (180) is not the failure.

100k + lifecycle: PASS. Seal was run by Task 14 agent (emitted `PERFORMANCE_FAIL` in `final-verdict.md`) — **operator asked not to seal**; no QUALIFIED claimed. Campaign evidence preserved.

## Isolation results

### 1. RSS trend and segments
- Post-warmup RSS rises ~3.1–3.4 MiB over ~3600s in all modes.
- Segment medians step up ~0.7–0.8 MiB per third (P0: 43.4 → 44.2 → 44.9).
- **Slope decelerates:** first 1800s OLS ~4.3–4.5 MiB/h; after 1800s ~1.8–2.1; last 600s ~0.15 (P0) / ~0.8–1.0 (P1/P2). Growth is **not** steady linear forever; early window dominates.

### 2. Stepwise allocator signature (strong)
- Across P0/P1/P2: **9 jumps ≥0.4 MiB** at nearly identical wall times.
- Early cluster every **~100s** (400, 500, 600) then every **~500s** (1100…3610).
- Median step between samples ≈ 0; p95 |step| ≈ 0.02 MiB — background is flat; slope is carried by **few large steps**.
- Matches `snapshot_every=200` ticks @ 2 Hz ≈ **100s** for the early cluster. Later 500s cadence needs further mapping (5× snapshot period or SQLite/allocator batching).

### 3. Python heap vs native RSS
- Not instrumented in this campaign (`tracemalloc` / `jemalloc` not attached).
- **Next probe (no freeze change yet):** short soak with `tracemalloc` + `/proc/self/smaps_rollup` sampled beside VmRSS.

### 4. SQLite / WAL
- **`database_growth_mib` ≈ 39 MiB in all three modes** — strongest common-path quantitative signal.
- Soak DBs end ~50–54 MiB file size; WAL active during run.
- Candidate: event/journal/snapshot retention in SQLite, not renderer.

### 5. Temporal snapshots / caches / journals
- Production `snapshot_every=200` + `prune_snapshots` on runtime path.
- Forced `snapshot_if_due(force=True)` at soak end only (harness).
- Dedup/temporal structures: not directly sized in soak samples; ring occupancy **0 on P0**, **64 on P1** — frame ring cannot explain P0 growth.

### 6. Renderer-independent queues
- P0 (no expression) already fails with same slope family as P1.
- P2 adds ~**+9 MiB absolute level**, slope only ~+0.17 vs P0 — **Tkinter is not the growth driver**.

### 7. GC behavior
- Not profiled this run. Stepwise jumps more consistent with snapshots/allocator arenas than CPython GC spikes (usually smaller/noisier).

### 8. Warmup vs linear
- JSONL samples begin at t≈300 (post-warmup boundary); early post-warmup slope is highest.
- Last 10 minutes much flatter (especially P0) — argues against unbounded linear leak as sole story; **segment-growth gate still fails** under frozen S3 rules.

### 9. Slope calculation distortion
- Reported robust slope ~1.90 with **very wide CI** crossing zero (e.g. P0 CI ≈ [-3.3, 10.5]) — S3 marks inconclusive and extends to max, then fails on `sustained_segment_growth`.
- Simple OLS on same window is steeper (~2.56) — method differs, but both exceed 1.0.
- Stepwise jumps can inflate segment-median staircase even when late window is flat.

## Working hypotheses (ranked)

1. **Common SQLite growth** (events/snapshots/journals/WAL) shared by P0/P1/P2 (~39 MiB file growth).
2. **Periodic snapshot / retention interaction** producing ~100s then ~500s RSS steps (allocator committing pages for DB or snapshot blobs).
3. **Measurement/gate sensitivity:** wide CI + segment rule fails a decelerating/stepwise process that may be “bounded residency” in D-002P sense — still a formal FAIL under frozen thresholds; fixing may be retain/prune policy and/or gate semantics via **invalidate**.
4. **Not** D-010 anticipation-specific; **not** Tkinter-specific.

## Do not do yet

- No source patch under `3178815`.
- No QUALIFIED.
- No new Stage B until root cause chosen and reviewed.

## Required next sequence (operator)

```text
preserve failed evidence  ✓ (this campaign)
→ diagnose root cause     ✓ (this note; deepen with tracemalloc/smaps + sqlite page accounting)
→ patch and test
→ independent review
→ new Stage B freeze + formal_execution_id
→ rerun Gate 13
```

Artifacts: `docs/evidence/d010/gate13-rss-diagnosis.json`, this file.
