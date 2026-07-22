# CURRENT.md

## Active directive
- ID: D-20260722-1330-d006-task6-merge-reliability
- Project directive: UMBRA-D-006
- Goal: Task 6 — non-destructive merge/split provenance + reliability revision + partner swap detection
- Status: done
- Acceptance: met — merge_hypotheses/split_hypothesis with ledger provenance links; social_partner_swap_detected; reliability anomaly/repeated/recovery rules; 7 brief tests pass; full suite green
- Touched files: umbra_core/social/engine.py, umbra_core/persistence.py, umbra_core/events.py, tests/test_d006.py, docs/superpowers/specs/2026-07-22-umbra-d006-social-contingency-design.md, .superpowers/sdd/task-6-report.md, .agent/*
- Next action: Task 7 — soft social proposals + hybrid actuation wiring in runtime

## Repo facts needed now
- Mimir project: 7777645d52a91b49
- Mimir task: 88c66c26db814c6aa28779f5e3544510
- Reliability: single NONE → -reliability_anomaly_weaken (0.08); repeated NONE (none_count≥2) → proportional loss; recovery CONTINGENT after failures → 1.25× gain boost
- Merge/split: sources archived INACTIVE; social_hypothesis_provenance_links table for full lineage
- Swap: swap_detect_score_margin=0.15, swap_recency_ticks=64

## Last validation
- Command: pytest tests/test_d006.py -q ; pytest tests/ -q
- Result: 40 passed ; 218 passed

## Open blockers
- mimir_validation_run task-scoped runner (same precedent as Tasks 4/5)
