# UMBRA-D-013T-R1 - Independent-review closure

## Verdict

D013T_R1_UNRECOVERABLE_PATH_CONFIRMED

This is a non-formal causal review closure. It does not authorize a formal P0,
a new formal tag, a D-013S retry, or a new V2 contract.

## Baseline and preservation

- Starting HEAD: 52735efe7ccfb0a12f992ae5373004dc5638c57e
- D-013S baseline preserved: 05860573b141323640c78419a6ddae3736e9473a
- D-013S tag: umbra-d013s-v2-formal-baseline-0586057
- Contract: P0_RECOVERY_CONTRACT_V2
- Contract fingerprint unchanged: 511c6f56d1cde7c5c28e290e7b1679eea85494b642eb57b5642a5295bbdd2ad2

## Finding 1: residual same-focus hole

The published D-013T implementation reproduced the review finding before
correction:

- energy before: 0.0505
- focus: energy
- candidate: SIGNAL_ASSISTANCE
- known energy effect: -0.001
- projected energy: 0.0495
- critical floor: 0.05
- pre-correction guard: accepted because energy remained exempt for this
  capability

The correction generalizes the exemption rule by known energy-effect sign.
When energy is the recovery focus, every candidate with a known negative energy
effect is evaluated against the energy critical boundary. Positive restorative
actions such as CHARGE remain eligible. No capability-name special case,
threshold, or outcome effect was added.

## Finding 2: terminal unreachable path

The extended real-runtime continuation was not stopped at six ticks. It
continued until the first critical energy boundary failure:

1. SIGNAL_ASSISTANCE admitted and verified; energy effect -0.001.
2. Five subsequent signal attempts denied by the existing six-tick cooldown.
3. A second assistance signal was admitted and verified; it still only emitted
   the existing social-signal event and consumed energy.
4. One more signal attempt was denied by cooldown.
5. The organism reached the critical energy boundary at tick 9. No CHARGE
   occurred, no route became feasible, and no authoritative resource or energy
   change resulted from assistance.

SIGNAL_ASSISTANCE is therefore NO as a genuine state-changing recovery path in
this frozen fallback configuration. It is a social-signal primitive, not an
energy-restoration action. The terminal classification is
NO_RECOVERY_PATH_AVAILABLE for the D-013S tick-409-equivalent low-reserve,
distant-resource state.

## Preserved reachable behavior

The reachable bounded continuation still completed 100 ticks with:

- minimum energy: 0.198
- terminal energy: 0.598
- verified CHARGE recoveries: 6
- critical crossing: false
- identity preserved
- governance bypass attempts: 0
- persistence chain validation: pass

## Integrity

- production change: only the effect-based same-focus guard in
  umbra_core/arbitration.py
- tests: R1 safety coverage plus D-002 learning-test isolation from unrelated
  low-energy depletion
- thresholds changed: false
- OUTCOME_EFFECTS changed: false
- evaluator/V2 changed: false
- D-013S and historical evidence changed: false
- .agent/RECORD.md changed: false
- .agent/LIBRARY_REVIEW.md changed: false
- formal P0 launched: false
- formal tag created: false

The immediate unsafe-action defect is corrected. Integrated P0 viability remains
blocked because the existing architecture can enter an unrecoverable state.
Any solution requiring anticipatory homeostasis, route planning, alternative
resource search, or partner rescue requires a separate Architect decision and
external prior-art review.
