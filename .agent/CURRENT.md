# CURRENT.md

## Active directive
- ID: D-20260720-umbra-d001-invariant-companion-core
- Project directive: UMBRA-D-001
- Goal: Implement and validate the minimum persistent UMBRA invariant companion core
- Status: partial — foundation implemented; 6h soak running for Gate 9 QUALIFIED seal
- Acceptance: Gates 0–8,10 PASS; Gate 9/11 PARTIAL (soak incomplete)
- Touched files: umbra_core/, tests/, experiments/d001/, docs/evidence/d001/, .agent/*
- Next action: Await soak-6h-summary.json; then re-seal QUALIFIED if metrics hold

## Repo facts needed now
- Mimir project ID: 7777645d52a91b49
- Mimir task ID: 32cbec622ee34877977ba95ff10becf8
- Starting commit: 813b9d6a3f1cbee159d0e421bf745a2039626dcf
- Verdict: UMBRA_D001_PARTIAL_FOUNDATION
- Ending commit: cc174daa6a1b1c2163bbff0e6c89585124b360d8
- Soak: RUNNING under /tmp/umbra_soak/soak6h.sqlite

## Last validation
- Command: `PYTHONPATH=. python3 -m pytest tests/test_d001.py -q`
- Result: 33 passed

## Open blockers
- Gate 9 six-hour soak not yet complete (process running)
