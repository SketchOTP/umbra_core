# CURRENT.md

## Active directive
- ID: D-20260723-1845-d008-task13-inline-gates
- Project directive: UMBRA-D-008
- Goal: Task 13 Gates 1–11 full-schema evidence (≥100 paired seeds); no QUALIFIED
- Status: in_progress — full matrix run after smoke (Gates 1/4/5 metrics green at 2 seeds)
- Acceptance: all Gate 1–11 + render-coherence + regression pass; schema-compliant; validator OK; commit only on pass; Task 14 NOT authorized until independent review
- Touched files: experiments/d008/{run_experiment.py,evidence.py,validate_evidence.py}, docs/evidence/d008/*, .agent/*
- Next action: complete 100-seed `run_experiment` → validate_evidence → pytest → commit if pass → independent review

## Repo facts needed now
- Tip before Task 13 evidence: 1506fa8
- Mimir task: 23f68202600c401c9efb42740622b73e (parent D-008: cbbb61834c98463cb70fb9254ba08ea2 — do not close)
- Smoke: D008_SEEDS=2 metrics would pass thresholds; file pass=false until seeds≥100

## Last validation
- Command: D008_SEEDS=2 D008_TICKS=40 D008_ALLOW_SMOKE=1 python3 -m experiments.d008.run_experiment
- Result: exit 1 (incomplete seeds by design); Gate1 c0=1.0 c9=0; Gate4 sep≈0.31; Gate5 vocab=1.0

## Open blockers
- Full 100-seed matrix in progress
- Independent review required before TASK 14 AUTHORIZED
- python3-tk missing for Task 14 soak
