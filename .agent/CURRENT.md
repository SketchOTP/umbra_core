# CURRENT.md

## Active directive
- ID: D-20260720-umbra-d001c-performance-closeout
- Project directive: UMBRA-D-001C (parent UMBRA-D-001)
- Goal: Commit retention-v1; Run B 6h soak; seal D-001 only if all gates pass
- Status: in_progress — Run A closed as v0 perf-only; committing retention-v1 then starting Run B
- Acceptance: Run B provenance + Gate9 thresholds; authoritative cadence; ledger/hash/restart/replay; full tests; QUALIFIED only if all pass
- Touched files: umbra_core/events.py, runtime.py, persistence.py, tests/, experiments/d001/, docs/evidence/d001/, .agent/*
- Next action: Commit → start Run B → await SOAK_B_DONE → closeout_run_b → seal or fail

## Repo facts needed now
- Mimir project ID: 7777645d52a91b49
- Mimir task ID: a9d8858e78824663ae88103cf735c025
- Mimir task version: 2
- Prior D-001C task: 15d8a6968dda486183ed8ba21e322753
- Foundation commit: e9fed18ec8c1a72db05b2efe6d93502a2ba6d7c9
- Formal state: UMBRA_D001_PARTIAL_FOUNDATION; D-002 AUTHORIZED: NO
- Run A: performance-only retention v0; gate9_performance_pass=false (rss_slope_le_1)
- Run B DB: .soak/run_b.sqlite (gitignored)

## Last validation
- Command: PYTHONPATH=. python3 -m pytest tests/test_d001.py tests/test_d001c_closeout.py -q
- Result: 39 passed, 3 skipped

## Open blockers
- Run B 6h soak not started until retention-v1 commit lands
- QUALIFIED blocked until Run B passes all Gate 9 + retention gates
