# UMBRA-D-014A evidence pointer

- Directive: `UMBRA-D-014A`
- Baseline and remote master: `4bc55bc91cef5623f20fe78f97408e4d339f58b3`
- Parent formal result: `UMBRA_D014_PHYSIOLOGICAL_VIABILITY_FAIL`
- Verdict: `D014A_CAUSE_CONFIRMED_REMEDIATION_REQUIRES_BROADER_ARCHITECTURE`
- Recommendation: `BROADER_RECOVERY_ARCHITECTURE_REQUIRED`
- Evidence root: `/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d014a-fatigue-recovery-r1/`

## Result

The exact D-014 failure was reproduced for R0 seed `41241905`. The first
critical fatigue crossing was at tick `813` during `POST_DRIFT`, from
`0.9485000000000022` to `0.9505000000000022`. The failed REST outcome then
added another `+0.002`; it was not the first crossing.

The trace confirmed a policy-visible REST threshold could select REST while
authoritative execution returned `not_at_rest`. A verified denial was recorded,
but the fatigue path did not change the next candidate, producing a stationary
failed-REST corridor and `no_safe_action` at tick 812.

An evaluator-only denial-aware APPROACH handoff rescued the failing seed through
7,200 ticks with no critical crossing. The same local production correction was
then replayed across all six originally attempted D-014 R0 seeds and introduced
new stimulation failures in seeds `5366620` and `49452783`. It was reverted.

The causal signal is accepted, but a safe remediation requires broader
multi-need recovery handling. No formal D-014 rerun, D-013/AX work, or automatic
broader remediation follows from this closeout.

## Validation and integrity

- Focused denial/recovery tests: 5 passed.
- D-011/D-012 compatibility: 42 passed.
- D-009 validator: PASS.
- D-010 validator: PASS.
- Authority 3.0: PASS.
- Governance: PASS.
- Full path-safe suite: 872 passed, 2 skipped.
- Production, tests, thresholds, historical evidence, `.agent/RECORD.md`, and
  `.agent/LIBRARY_REVIEW.md` are unchanged from the D-014 closeout commit.
- No formal tag or formal rerun was created.
- Notion closeout was not updated in this session because no Notion connector
  was available.
