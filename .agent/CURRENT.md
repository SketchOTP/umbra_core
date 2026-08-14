# CURRENT.md

## Active directive
- ID: D-20260813-UMBRA-CC-001
- Project directive: UMBRA-D-000X
- Goal: Reconcile UMBRA-CORE against broader ALife prior art and establish informed-reuse recommendations without changing qualified evidence or production authority.
- Status: D-000X complete — prior-art closeout and independent read-only review approved; CC-2 remains unauthorized.
- Acceptance: 14 systems classified, 7 source audits pinned, novelty/duplication/reuse reconciled, consistency validator PASS, independent review APPROVE, no production integration, historical evidence unchanged.
- Touched files: CC-1 governance plus `docs/prior-art/alife-extended/*`; production and sealed evidence untouched.
- Next action: operator review; do not begin CC-2 without explicit authorization.

## Repo facts needed now
- Qualified release baseline: D-009; seal `af35371`; governance closeout `0880537`.
- D-010 is deferred: `UMBRA_D010_PERFORMANCE_FAIL`; it is not a D-011 prerequisite.

## Last validation
- Command: baseline audit; D-009 and D-010 evidence validators; verdict hash checks; process/storage checks.
- Result: D-009 validator PASS (14 files, 3,300 raw rows); D-010 validator PASS (zero errors, 1,900 raw rows); verdict hashes match; no active UMBRA/D-009–D-012 process; storage 86% used / 34 GiB free.

## Open blockers
- Mimir V2 lifecycle tools (`mimir_project_resolve`, `mimir_task_begin`, and related tools) are unavailable in this session.
- Mimir project ID remains canonically bound as `7777645d52a91b49`; required V2 resolve/begin/context/validation/evidence/close calls cannot be performed or claimed.
- Pre-existing untracked `.agent/LIBRARY_REVIEW.md` is unexplained for this task and must not be modified or removed.
- CAX source/license is verified at `maxencefaldor/cax@1af1185`; no production integration or CC-2 authorization follows from the closeout.
- D-000X review approved with documented `UNKNOWN_AFTER_REVIEW` source questions for Aevol, Tierra, Stringmol, and Evo2Sim; these do not authorize direct reuse.
