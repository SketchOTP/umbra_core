# CURRENT.md

## Active directive
- ID: D-20260727-1356-umbra-d012b-adaptive-fail-fast-p0
- Project directive: UMBRA-D-012B
- Goal: Execute one formal adaptive fail-fast P0 through the qualified distinct-worker supervisor.
- Status: complete — `UMBRA_D012B_P0_INTEGRITY_FAIL`; formal P0 stopped at the first failed invariant.
- Acceptance: met for the authorized non-pass path — stopped immediately on critical physiology, preserved evidence, left P1/P2 unlaunched, kept D-010 disabled and unchanged, and cleaned all formal processes/locks/sockets/ownership.
- Touched files: experiments/d012, tests/test_d012_process_boundary.py, docs/evidence/d012, governance.
- Next action: stop; no D-012C, P1, P2, diagnosis, or relaunch is authorized.

## Repo facts needed now
- Qualified release baseline: D-009; seal `af35371`; governance closeout `0880537`.
- D-010 is deferred: `UMBRA_D010_PERFORMANCE_FAIL`; it is not a D-011 prerequisite.

## Last validation
- Command: formal P0; `pytest -q`; governance/schedule/diff/process checks.
- Result: formal execution stopped at 100.061 active seconds on `invalid_physiological_state`; tick 191 cleanup snapshot energy 0.0015 < 0.05 critical bound; full suite 688 passed/1 frozen D-010 failure/2 skipped/2 warnings; D-010 79-error fingerprint unchanged; cleanup PASS.

## Open blockers
- Mimir V2 lifecycle tools (`mimir_project_resolve`, `mimir_task_begin`, and related tools) are unavailable in this session.
- Mimir project ID remains canonically bound as `7777645d52a91b49`; required V2 resolve/begin/context/validation/evidence/close calls cannot be performed or claimed.
- P1 and P2 are unauthorized. D-010 is deferred, disabled, excluded, and its frozen unrelated full-suite failure must not change.
- Formal P0 first failed invariant: invalid physiological state. D-012 remains unqualified; D-012C is unauthorized.
