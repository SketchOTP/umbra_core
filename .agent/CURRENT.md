# Current Project State

## D-014C closeout

UMBRA-D-014C is terminal and returned to Architect from baseline
`d60cbc7d750697f45f94a63713c1408e0a992277`.

- Verdict: `D014C_AUTHORITY_ORDER_CONFIRMED_BUT_RECOVERY_DEFECT_PERSISTS`.
- A0-A9 reconstruction found downstream world-model replacement contributory
  in the seed `79871850` failure; the `27526357` failure did not show an
  authority-order replacement at its failure decision.
- The conditional final-boundary correction was evaluated but failed the
  required eight-seed R0, 7,200-tick gate. Four required seeds failed before
  7,200 ticks; four completed. The correction was reverted.
- Evidence: `/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d014c-authority-path-r1/`.
- Validation: D-009 and D-010 validators PASS; D-012 readonly validation and
  schedule validation PASS; full suite not run after the failed gate.
- No production correction, formal tag, formal P0, retry, threshold change,
  or historical evidence change was retained. Protected RECORD and
  LIBRARY_REVIEW were preserved.

Integrated viability remains unqualified. Return to Architect; no next
experiment is authorized by this closeout.

## Current stage
Authority 3.0 active; D-014C is terminal and returned to Architect.

## Current objective
Return to Architect after the D-014C bounded authority-order diagnosis. Do not
launch formal D-014 work or begin another remediation automatically.

## Active directive
D-014C is terminal from baseline `d60cbc7d750697f45f94a63713c1408e0a992277`.

## Terminal result
`D014C_AUTHORITY_ORDER_CONFIRMED_BUT_RECOVERY_DEFECT_PERSISTS`.

Last updated: 2026-08-22T14:52:00-04:00

## D-012R closeout

UMBRA-D-012R completed one bounded, non-formal current-stack integrated
viability recheck from baseline
`90dc9b939e6128b80641cab5c91aa926336451f1`.

- Matched cases: L1/L2 with D-010 disabled; T1/T2 with D-010 enabled.
- Seed `12012`, S2 habitat, event-0 prefix, maximum 400 logical ticks.
- All four cases completed 400 ticks without critical physiology failure.
- L1/L2 and T1/T2 reproduced selected actions and physiology. L→T had a
  common 400-tick behavioral/physiology prefix; temporal state was present in T
  without observed action or physiology divergence.
- Historical D-012B2 tick-181 energy collapse was not reproduced. H→L first
  materially diverged at tick 34; current L tick 181 energy was `0.6075` with
  executable resource distance `0.2610`, versus historical `0.0485` after
  `MOVE` at distance `3.8042`.
- Verdict: `D012R_HISTORICAL_D012_PHENOTYPE_NOT_REPRODUCED_CURRENT`.
- Evidence: `/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d012r-current-stack-viability-r1/`.
- Validation: focused D-012/D-010 compatibility 168 passed; D-009/D-010
  validators, Authority 3.0, and governance PASS.
- No production, tests, thresholds, formal tag, formal P0, or historical
  evidence changed. No retry occurred.

Return to Architect. Integrated viability remains unqualified; no next
experiment is automatically authorized.

## D-010Q5 closeout

UMBRA-D-010Q5 completed one fresh current-baseline temporal-continuity
qualification generation from repository baseline
`0eda4fc275a32433fe5edc7744bc8bf60955a727`.

- Accepted Q4 production source remains the parent `85afe181e5bdbea6008b48813da4013e9ac54086`.
- Executor: serial, `D010_WORKERS=1`; multiprocessing was not used.
- Development serial repeat preflight: PASS; executor classification:
  `SERIAL_EXECUTION_SCIENTIFICALLY_EQUIVALENT`.
- Formal execution ID: `d010q5-current-baseline-r1`; exactly one invocation;
  1,900/1,900 rows completed; scientific change count 0.
- Gates 0–12: PASS; accelerated 100,000 ticks: PASS; renderer lifecycle:
  100 cycles PASS; S3 P0/P1/P2: PASS.
- Verdict: `UMBRA_D010_TEMPORAL_CONTINUITY_QUALIFIED`.
- Evidence: `/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d010q5-current-baseline-r1/`.
- Validation: D-009/D-010 evidence validators PASS; focused D-010 133 passed;
  D-001–D-011 compatibility 615 passed, 2 skipped; full path-safe suite
  872 passed, 2 skipped; Authority 3.0 and governance PASS.
- Cleanup: Q5 temporary roots and workers removed; historical evidence,
  production code, thresholds, protected records, and formal tags unchanged.

Q5 qualifies current-baseline D-010 temporal continuity only. It does not
qualify integrated long-horizon organism viability or project completion.
Historical D-010 results remain authoritative for their original generations.

## Current stage
Authority 3.0 active; D-010Q5 is terminal and returned to Architect.

## Current objective
Return to Architect after the accepted current-baseline D-010 qualification.
No automatic D-012 continuation, D-013 reopening, formal tag, or remediation
is authorized by this closeout.

## Active directive
D-010Q5 is terminal and returned to Architect from repository baseline
`0eda4fc275a32433fe5edc7744bc8bf60955a727`. No retry or second generation was
performed.

## Terminal result
`UMBRA_D010_TEMPORAL_CONTINUITY_QUALIFIED`.

## D-010Q4 closeout

UMBRA-D-010Q4 completed its bounded temporal-authority migration and stopped
at the single formal execution boundary from baseline
85afe181e5bdbea6008b48813da4013e9ac54086.

- Remediation commits: d808a7d8057692b5db4bb02315224bb881bc0877 and
  85afe181e5bdbea6008b48813da4013e9ac54086.
- Current registry: 42 sites; O=42, T=0, B=0, unclassified=0; semantic
  fingerprints present.
- Validation: focused D-010 133 passed; D-001-D-011 compatibility 657 passed,
  2 skipped; full path-safe suite 872 passed, 2 skipped; D-009/D-010,
  Authority 3.0, and governance validators PASS.
- Formal execution: exactly one invocation created execution ID
  d010q4-current-baseline-r1, produced zero formal rows, and failed at
  multiprocessing worker startup with ConnectionResetError [Errno 104].
- Verdict: D010Q4_EXECUTION_STOP_UNRESOLVED. No retry was performed and no
  scientific D-010 qualification verdict is claimed.
- Evidence: /mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d010q4-current-baseline-r1/.
- Formal tag: none. Historical D-010 PERFORMANCE_FAIL, thresholds, and
  historical evidence remain authoritative.

## D-010Q3 closeout

UMBRA-D-010Q3 stopped at the hard temporal-authority gate from baseline
8035fe75250dcaefcc6fdb40b395206f111584ff.

- Verdict: D010Q3_TEMPORAL_AUTHORITY_MIGRATION_REQUIRED.
- Current source scan: 42 runtime-tick sites; semantic adjudication 40 O and
  2 unmigrated B sites.
- Offending sites: umbra_core/runtime.py:468 (_organism_age_tick) and
  umbra_core/runtime.py:1333 (_tick_once_body -> Arbitrator.select).
- Evidence: /mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d010q3-authority-reconciliation-r1/.
- Formal generation: not started; execution ID: none; formal tag: none.
- Validation: D-009, D-010, Authority 3.0, and governance PASS; short
  disk-backed full suite 867 passed, 2 skipped, 1 inherited D-010 registry
  failure.
- Production, thresholds, historical evidence, RECORD, and LIBRARY_REVIEW
  remain unchanged.

The next decision is temporal-authority migration and a separately authorized
fresh qualification. Do not launch D-010 formal work from this stop.

## Current stage
Authority 3.0 active; D-010Q4 is terminal and returned to Architect.

## Current objective
Return to Architect after the Q4 formal worker-startup stop. Do not retry the
formal execution automatically. The Q4 temporal-authority migration is frozen
and the remaining blocker is operational execution readiness.

## Active directive
D-010Q4 is terminal and returned to Architect from repository baseline
85afe181e5bdbea6008b48813da4013e9ac54086. No retry, new formal invocation,
dependency installation, or further remediation is authorized by this closeout.

## Terminal result
`D010Q4_EXECUTION_STOP_UNRESOLVED`. The historical
`UMBRA_D010_PERFORMANCE_FAIL` remains permanent and is not superseded.

## Scientific boundary
AL/AO evidence is retained as a policy-provenanced shadow recoverability
representation, not as an executable rescue policy. AV found no demonstrated
local production action-selection correction and recommends
RECOVERABILITY_REPRESENTATION_ONLY.

## Evidence
AXR forensic evidence is at /mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d013axr-execution-stop-r1.
The preserved incomplete AX tree remains at /mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d013ax-bounded-coordination-r1.
Tracked AXR pointer: docs/evidence/d013axr-execution-stop/README.md.

## AXR boundary
AXR was read-only operations/scientific-integrity adjudication. AXR executed
zero scientific branches and did not modify production, tests, experiments,
historical evidence, thresholds, protected records, formal tags, or formal P0.
Do not resume/relaunch AX, repair the harness, begin D-013AY, or launch formal
work without separate Architect authorization.

## Protected state
.agent/RECORD.md, .agent/LIBRARY_REVIEW.md, production source, experiments,
tests, historical evidence, thresholds, verdicts, D-012 contracts, and formal
tags were preserved unchanged. No formal P0 or formal tag was created.

## AXH closeout

UMBRA-D-013AXH is complete and returned to Architect.

- Verdict: `D013AXH_DURABLE_HARNESS_QUALIFIED`.
- Recommendation: `CLEAN_AX_RERUN_SAME_PROTOCOL_CANDIDATE` only; a clean AX rerun is not authorized by AXH.
- Evidence: `/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d013axh-harness-remediation-r1/`.
- Synthetic campaign: PASS; focused AXH tests: 13 passed; D-013 family: 171 passed; D-012 process checks: 35 passed.
- Path-safe full suite: 867 passed, 2 skipped, 1 inherited D-010 runtime-tick inventory failure.
- AX scientific branches executed under AXH: 0.
- Protocol fingerprint preserved: `b3b065c2fcc06f9d1d7e4cdde59eac0b69919c9c31427f3f5456249c8c0cf07`.
- Production, historical evidence, thresholds, formal tags, formal P0 state, RECORD, and LIBRARY_REVIEW remain unchanged.

Return to Architect. Do not rerun AX, begin D-013AY, or launch formal work from AXH.


## D-010Q closeout

- Execution: `d010q-current-baseline-r1`; baseline and GitHub `master`:
  `0d3234002a9ddd49fe31a226e2943c2ecf5552bf`.
- Verdict: `UMBRA_D010_PERFORMANCE_FAIL`.
- Functional: 1,900/1,900 rows; Gates 0–12 PASS.
- Accelerated: 100,000 ticks PASS; renderer lifecycle failed closed before
  execution because `libtk8.6.so` / `python3-tk` is unavailable.
- P0/P1/P2: not executed. Retries: 0. Formal tag: false.
- Validation: D-010 focused 129 passed; prior-capability suite 512 passed,
  2 skipped; full suite 868 passed, 2 skipped; D-009/D-010/Authority 3.0/
  governance PASS.
- Evidence: `/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d010q-current-baseline-r1/`;
  pointer `docs/evidence/d010q-current-baseline/README.md`.
- Integrity: production, tests, historical evidence, thresholds, RECORD, and
  LIBRARY_REVIEW unchanged.
- Next: return to Architect; no automatic remediation or formal retry.

## D-014 terminal closeout — current snapshot supersession

UMBRA-D-014 is terminal and returned to Architect.

- Verdict: `UMBRA_D014_PHYSIOLOGICAL_VIABILITY_FAIL`.
- Baseline: `f59c767ff758fb8d957581c0420a5271f3192f3b`.
- Formal freeze commit/tag: `b225a759399069d1a7600a4f19adb3c0ce8baa89` /
  `umbra-d014-formal-baseline-b225a75`.
- Execution: `d014-integrated-stability-r1`; one invocation; 6/32 rows
  attempted, 5 complete and 1 failed.
- First failure: R0 seed `41241905`, tick 813; fatigue
  `0.9525000000000022` crossed the existing critical high boundary `0.95`
  after verified failed REST (`reason=not_at_rest`).
- No retry, reseed, remediation, production change, threshold change, or
  continuation occurred. The real-time soak was not run after the failure.
- Evidence: `/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d014-integrated-stability-r1/`;
  pointer `docs/evidence/d014-integrated-stability/README.md`.
- D-009/D-010/D-011/D-012R compatibility, Authority 3.0, and governance
  validation passed; integrated D-014 qualification failed.
- Notion closeout was not updated in this session because no Notion connector
  was available.

Do not automatically start a D-014 retry, remediation, D-013/AX work, or a
new formal generation. Return to Architect.


## D-014A terminal closeout — current snapshot supersession

UMBRA-D-014A is terminal and returned to Architect.

- Baseline: `4bc55bc91cef5623f20fe78f97408e4d339f58b3`.
- Parent formal result: `UMBRA_D014_PHYSIOLOGICAL_VIABILITY_FAIL`.
- Exact R0 seed `41241905` failure was reproduced. The first critical fatigue
  crossing occurred at tick 813 during `POST_DRIFT`, before the failed REST
  outcome completed.
- The source-level REST selection/executability gap and missing denial-aware
  handoff were causally supported. Evaluator-only CF1 rescued the failing seed
  through 7,200 ticks, but the same local production correction introduced new
  stimulation failures in two previously successful R0 controls.
- Terminal verdict:
  `D014A_CAUSE_CONFIRMED_REMEDIATION_REQUIRES_BROADER_ARCHITECTURE`.
- The attempted production correction was reverted. Production, tests,
  thresholds, historical evidence, `.agent/RECORD.md`, and
  `.agent/LIBRARY_REVIEW.md` remain unchanged from the D-014 closeout commit.
- Evidence: `/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d014a-fatigue-recovery-r1/`;
  pointer `docs/evidence/d014a-fatigue-recovery/README.md`.
- Validation: focused recovery 5 passed; D-011/D-012 compatibility 42 passed;
  D-009/D-010/Authority 3.0/governance PASS; full path-safe suite 872 passed,
  2 skipped.
- Notion closeout was not updated in this session because no Notion connector
  was available.

Do not automatically start another D-014 generation, a broader recovery fix,
D-013/AX work, or formal P0. Return to Architect.
