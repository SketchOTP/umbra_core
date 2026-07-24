# CURRENT.md

## Active directive
- ID: D-20260724-1527-d010-task12-stage-b-freeze
- Project directive: UMBRA-D-010
- Goal: Task 12 — Stage B freeze complete (last source-changing commit)
- Status: complete
- Freeze tip: `6943981` (`6943981c...` full: run `git rev-parse HEAD` on freeze commit)
- Task 13: evidence-only Gates 1–12 formal campaign from freeze tip
- Next action: Task 13 — run frozen formal harness; record `freeze_commit` in evidence manifest at run start

## Locked
- Design tip: `03e1269`
- Plan tip: `c1f71bb7e6ae58459c08585558a491fcae8b8bea`
- Stage B freeze tip: `6943981`
- formal_execution_id: `d010-fe-stage-b-v1`
- Parent Mimir: `9adf61b087ea4fa6a90a1c3bd401a9b3` (open until Task 14 seal)
- Freeze rule: Tasks 13–14 evidence commits only

## Last validation
- Command: `python -m pytest -q` + `run_seal.py --contract-only`
- Result: 622 passed (2 skipped non-d010); d010 105 zero-skip; seal manifest_ok true

## Open blockers
- None
- Note: untracked `docs/evidence/d010/` smoke from Task 11 — do not commit as formal evidence
