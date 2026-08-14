# CURRENT.md

## Active directive
- ID: D-20260814-UMBRA-CC-006
- Project directive: UMBRA-CC-006
- Goal: Validate a research-only discovery/qualification firewall contract before any automated discovery or ASAL prototype.
- Status: CC-6 complete — research-only discovery/qualification firewall independently approved; no ASAL, optimizer, production refactor, formal qualification, or historical evidence mutation authorized.
- Baseline: `umbra-cc-006-baseline-6b6cdd2` targets `6b6cdd23fd77c9d686a8eae953e84bf3afeaa3b0`.
- Acceptance: explicit zones/partitions; embargo rejection; protected-variable default-deny; frozen evaluator; immutable candidate quarantine; provenance; write isolation; contamination prevention; blind-validation design; 26+ fail-closed faults; prior validators passing; independent review; GitHub publication.
- Touched files: CC-6 research implementation, CC-6 dossier, and append-only governance records; `.agent/LIBRARY_REVIEW.md` preserved.
- Next action: operator review of the published CC-6 dossier only; next phase remains unauthorized.

## Last validation
- Command: CC-6 harness; D-000X; CC-2; CC-3; CC-4; CC-5; D-009; D-010; focused D-009 tests.
- Result: CC-6 PASS; 26/26 faults detected, zero silent failures; prior contracts PASS; D-000X/D-009/D-010 PASS; focused D-009 4 passed, 104 deselected.

## Prior directive
- ID: D-20260814-UMBRA-CC-005
- Project directive: UMBRA-CC-005
- Goal: Validate a research-only multi-cell/multi-seed aggregation contract around qualified D-009 gate 7.
- Status: CC-5 complete — research-only multi-cell aggregation contract independently approved; production authority, D-009 definitions, historical evidence, D-010, and D-012 unchanged.
- Baseline: `umbra-cc-005-baseline-2f7725e` targets `2f7725ea5de58830ddc9ace97905fdef2fd0ff8a`.
- Scope: four cells C0/C7 × S14 × H1/H7, seeds 1–100; research-only shadow aggregation; no qualification claim.

## Prior directive
- ID: D-20260814-UMBRA-CC-003
- Project directive: UMBRA-CC-003
- Goal: Validate a research-only restart/replay contract around the existing qualified D-009 C0/S10 clean close/restart route.
- Status: CC-3 complete — research-only restart/replay contract independently approved; production authority, historical evidence, D-010, and D-012 unchanged.
- Baseline: `umbra-cc-003-baseline-5a15caf` targets `5a15caf27435275c7bf49ad506f7e691e41c30a3`.
- Touched files: CC-3 dossier and `research/course_correction/cc3_restart_replay_contract/*`; `.agent/LIBRARY_REVIEW.md` preserved.
- Acceptance: D-009 C0/S10 real route mapped; exact reference/shadow equivalence PASS; 21/21 fail-closed faults PASS; source proof PASS; D-000X/CC-2/D-009/D-010 validators PASS; focused restart/replay tests PASS; independent review APPROVE_WITHOUT_CRITICAL_OR_IMPORTANT_FINDINGS.
- Next action: operator review of published CC-3 commits only; no production refactor, ASAL, MABE2, external embodiment, D-010/D-012 remediation, or qualification claim.

## Prior directive
- ID: D-20260814-UMBRA-CC-002
- Project directive: UMBRA-CC-002
- Goal: Validate a read-only modular harness contract around the qualified D-009 C0/S0 scenario without changing production authority or historical evidence.
- Status: CC-2 complete — research-only shadow contract validated and independently approved; no production refactor authorized.
- Acceptance: real D-009 route mapped; isolated shadow/reference equivalence PASS; 11/11 fail-closed fault tests PASS; focused D-009 tests PASS; D-000X/D-009/D-010 validators PASS; protected paths unchanged; independent review APPROVE.
- Touched files: CC-2 governance plus `docs/course-correction/cc2-harness-contract/*` and `research/course_correction/cc2_harness_contract/*`; production and sealed evidence untouched.
- Next action: operator review of published CC-2 commits; do not begin ASAL, MABE2, external embodiment, D-010/D-012 remediation, or production harness refactoring.

## Repo facts needed now
- Qualified release baseline: D-009; seal `af35371`; governance closeout `0880537`.
- D-010 is deferred: `UMBRA_D010_PERFORMANCE_FAIL`; it is not a D-011 prerequisite.
- CC-2 baseline tag: `umbra-cc-002-baseline-8714c3` points to `8714c308c0cf87523ce77b75f936c6cc76bae102`; D-009 seal `af35371` is reference truth only.

## Last validation
- Command: baseline audit; D-009 and D-010 evidence validators; verdict hash checks; process/storage checks.
- Result: CC-2 harness PASS; 112 focused D-009 tests PASS; D-000X PASS; D-009 PASS (14 files, 3,300 raw rows); D-010 PASS (zero errors, 1,900 raw rows); protected paths unchanged.

## Open blockers
- Mimir V2 lifecycle tools (`mimir_project_resolve`, `mimir_task_begin`, and related tools) are unavailable in this session.
- Mimir project ID remains canonically bound as `7777645d52a91b49`; required V2 resolve/begin/context/validation/evidence/close calls cannot be performed or claimed.
- Pre-existing untracked `.agent/LIBRARY_REVIEW.md` is unexplained for this task and must not be modified or removed.
- CAX source/license is verified at `maxencefaldor/cax@1af1185`; CC-2 is now separately authorized as a research-only validation.
- CC-2 implementation: `e4b078a`; independent review: `APPROVE_WITHOUT_CRITICAL_OR_IMPORTANT_FINDINGS`.
- D-000X review approved with documented `UNKNOWN_AFTER_REVIEW` source questions for Aevol, Tierra, Stringmol, and Evo2Sim; these do not authorize direct reuse.
