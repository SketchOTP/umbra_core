# CURRENT.md

## Active directive
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
