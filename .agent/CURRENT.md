# CURRENT.md

## Active directive
- ID: D-20260722-1552-d006-task13-perf-seal
- Project directive: UMBRA-D-006
- Goal: Gate 12 performance (100k accelerated + 2h RUNTIME_READY VmRSS soak; social+memory+world enabled; social_history H0) and final UMBRA-D-006 seal
- Status: done — acceptance MET; UMBRA-D-006 sealed QUALIFIED
- Acceptance: MET — soak 7200.3s, rss_p95 40.54 MiB (<=180), slope 0.224 MiB/h (<=1.0), cpu 0.00348 frac (<=0.05), bounded; 100k restart_continuity True; pytest tests/ 258 passed 0 skipped; evidence-hashes covers design/thresholds/matrix/sources/tests/all results; verdict UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED; D-007 AUTHORIZED
- Touched files: experiments/d006/run_performance.py, experiments/d006/run_seal.py, tests/test_d006.py (Gate 12 unskipped), docs/evidence/d006/{performance-results,performance-100k,soak-2h-summary,soak-2h.jsonl,prior-seals,schema-manifest,evidence-hashes,final-verdict}, .agent/*, .superpowers/sdd/task-13-report.md
- Next action: none — UMBRA-D-006 closed QUALIFIED; D-007 authorized when opened

## Repo facts needed now
- Soak (social+memory+world, seed 7, H0, 2 Hz): rss_p95 40.54 MiB, slope 0.224 MiB/h, cpu 0.00348 frac, bounded, 7200.3 s
- 100k (seed 42): rss_p95 38.9 MiB, restart_continuity True, counts_bounded True, db ~187 MiB (not gated)
- Frozen thresholds: rss_p95_mib_max 180, rss_slope_mib_per_hour_max 1.0, cpu_mean_frac_max 0.05 (unchanged)

## Last validation
- Command: python experiments/d006/run_seal.py ; pytest tests/ -q
- Result: UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED; 258 passed 0 skipped; prior_seals_valid True

## Open blockers
- mimir_validation_run: "validation requires an active observed task" (precedent Tasks 4-12) — validated locally with pytest
