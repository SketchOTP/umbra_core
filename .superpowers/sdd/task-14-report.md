# Task 14 Report — Adaptive Performance (S3) + Final Seal

**Project directive:** UMBRA-D-009  
**Agent memory ID:** D-20260724-task14-d009-perf-seal  
**Parent Mimir:** `06b5b59709864e11bddb8c1da56dd66e` — **CLOSED** v17  
**Sub-task Mimir:** `d52577c3dfca4bbfaf774e62b662cb51` — **CLOSED** v2  
**Verdict:** `UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED`

## Commits

| Commit | Purpose |
|--------|---------|
| `a93cc55` | Performance harness + seal scripts |
| `c9090a9` | Gate 13 evidence (100k + P0/P1/P2 + jsonl) |
| `af35371` | Seal artifacts + QUALIFIED verdict |
| `2084be8` | Seal ending-commit hash bind |

## Gate 13 results (S3 adaptive)

| Step | Pass | Notes |
|------|------|-------|
| 100k accelerated | yes | rss_p95 within limit; habitat bounded; restart continuity |
| Renderer lifecycle (100×) | yes | Tk under `with_tk_display.sh` |
| P0 compatibility | yes | 2700s measured (+900s extension, rss_slope_ci_ambiguous) |
| P1 headless full D-009 | yes | 1800s measured |
| P2 Tkinter full D-009 | yes | 1800s measured; DISPLAY :99 |
| Recompose | yes | `performance-results.json` pass=true, smoke_scaled=false |

**Peak soak RSS p95:** 56.29 MiB (limit 180)  
**Peak soak slope:** 0.52 MiB/h (limit 1.0)  
**Tk incremental RSS p95:** 9.17 MiB (limit 128)

## Seal summary

| Check | Result |
|-------|--------|
| Gates 1–12 (Task 13) | PASS |
| Gate 13 performance | PASS |
| Prior seals D-001…D-008 | PASS |
| Zero-skip suite | PASS (519 passed, 0 skipped) |

**Note:** Seal must run under `with_tk_display.sh` so D-008 Tkinter tests do not skip (2 skips without DISPLAY).

## Harness fixes (vs D-008 port)

1. History plants (`_prepare_organism`) before `HabitatEngine` attach — avoids `habitat_engine_is_sole_writer` on first tick.
2. P0 uses `habitat_config=p0_compatibility_config()` with `condition=C0` for organism modules (C13 is habitat-only).

## Leftover processes

- Killed Task 14 Xvfb via `/tmp/umbra-d009-xvfb99.pid`
- Pre-existing unrelated Xvfb instances on :100–:107 remain (not started by this task)

## Worktree

Clean after governance commit (pending).

## Deviations

None.

## Next

Independent review before treating QUALIFIED as operator-final; D-010 not authorized until review.
