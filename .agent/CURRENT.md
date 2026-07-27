# CURRENT.md

## Active directive
- ID: D-20260727-1153-umbra-d012b1-energy-collapse-adjudication
- Project directive: UMBRA-D-012B1
- Goal: Determine the exact causal origin of the failed P0 energy collapse without relaunching formal P0.
- Status: complete — `UMBRA_D012B1_INTEGRATION_DEFECT_CONFIRMED`; `ARBITRATION_OR_GOVERNANCE_RECOVERY_FAILURE`; `REMEDIATED_AND_REVALIDATED`.
- Acceptance: Gates A-J met; 52-tick causal timeline, cleanup/cadence/recovery/opportunity audits, bounded R0-R3, one red/green integration fix, required regressions, hashes, and read-only APPROVE.
- Touched files: one production line in `umbra_core/arbitration.py`; D-012 diagnostic harness/tests/evidence; governance.
- Next action: stop; formal P0, P1, P2, and D-012C remain unauthorized.

## Repo facts needed now
- Qualified release baseline: D-009; seal `af35371`; governance closeout `0880537`.
- D-010 is deferred: `UMBRA_D010_PERFORMANCE_FAIL`; it is not a D-011 prerequisite.

## Last validation
- Command: required D-012/prior regressions, governance/schedule/diff checks, D-010 fingerprint, evidence hashes, process/ownership/socket audit.
- Result: D-012 33 passed; D-001/D-009/D-011 148 passed; governance/schedule/diff PASS; frozen D-010 79-error fingerprint unchanged `e531d099...af6082`; 15 D-012B1 hashes PASS; no live worker/socket/active ownership.

## Open blockers
- Mimir V2 lifecycle tools (`mimir_project_resolve`, `mimir_task_begin`, and related tools) are unavailable in this session.
- Mimir project ID remains canonically bound as `7777645d52a91b49`; required V2 resolve/begin/context/validation/evidence/close calls cannot be performed or claimed.
- P1 and P2 are unauthorized. D-010 is deferred, disabled, excluded, and its frozen unrelated full-suite failure must not change.
- Formal P0 relaunch is unauthorized. D-012 remains unqualified; D-012C is unauthorized.
