# CURRENT.md

## Active directive
- ID: D-20260723-1845-d008-task13-inline-gates
- Project directive: UMBRA-D-008
- Goal: Task 13 Gates 1–11 evidence
- Status: done — UMBRA_D008_TASK13_GATES_1_11_PASS; Task 14 blocked on independent review
- Acceptance: met (local); independent review pending
- Touched files: experiments/d008/{run_experiment,evidence,validate_evidence}.py, docs/evidence/d008/*
- Next action: Independent review of committed evidence → then Task 14 if AUTHORIZED

## Repo facts needed now
- Tip: de9fc10 (evidence); harness: 425e2c8
- software_commit in evidence: 425e2c8
- Parent Mimir: cbbb61834c98463cb70fb9254ba08ea2 (open)

## Last validation
- Command: run_experiment 100 seeds + validate_evidence + pytest d008 + d001–d007
- Result: all pass (2 tkinter skips remain for Task 14)

## Open blockers
- Independent review pending → TASK 14 AUTHORIZED: NO
- python3-tk missing for Task 14 soak
