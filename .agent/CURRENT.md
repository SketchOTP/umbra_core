# CURRENT.md

## Active directive
- ID: D-20260724-1536-d010-task13-gates-1-12
- Project directive: UMBRA-D-010
- Goal: Task 13 — formal Gates 1–12 evidence-only under Stage B freeze
- Status: **BLOCKED — freeze invalidate required**
- Freeze tip: `694398166b772b41f962bdb7afc90b3871a02c08`
- Task 12: complete / Approved @ `6943981`
- Next action: patch harness `_organism_cfg` condition wiring → new Stage B freeze → rerun Task 13

## Locked
- Design tip: `03e1269`
- Plan tip: `c1f71bb7e6ae58459c08585558a491fcae8b8bea`
- Parent Mimir: `9adf61b087ea4fa6a90a1c3bd401a9b3` (open until seal)
- Constraint: evidence commits only; no source edits under freeze tip

## Task 13 outcome
- Formal run aborted: `TemporalConfigError` on C11 integrated trace
- Root cause: harness passes C1–C13 as `OrganismConfig.condition`; production guard rejects
- Evidence: `docs/evidence/d010/formal-execution-manifest.json`, `formal-run-outcome.json`
- Gates 0–12: NOT_RUN; validator FAIL (0 raw rows)

## Last validation
- Command: `python experiments/d010/run_experiment.py` (full formal, no D010_TICK_CAP)
- Result: FAILED @ ~27s — harness/production guard mismatch on first ablation cell

## Open blockers
- Freeze invalidate: fix `experiments/d010/run_experiment.py` `_organism_cfg` + integration test; new Stage B freeze; rerun Task 13
