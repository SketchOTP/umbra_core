# D-013V Observation-Support Recoverability Envelope

Directive: UMBRA-D-013V
Baseline: `8bdd8f1c7ccd6db44845569e71cfeb469dd244d7`
Date: 2026-08-16
Scope: non-formal world-model/homeostasis integration correction

## Terminal verdict

`D013V_CORRECTION_FAIL`

The D-013S replay gate passed, and the smallest permitted support-envelope
correction was implemented and tested. The required 500-tick non-formal
continuation nevertheless crossed critical energy and did not demonstrate the
full sequence of anticipatory preservation, verified recovery, and release.
No formal viability claim is made.

## D-013S bounded replay

The last direct resource observation was tick 367. The sensor's declared
observation support was 10.0; generic `uncertainty` remained `1-confidence`
and was not converted into distance. Verified self-motion was taken from the
existing body transition verification and conservatively lower-bounded using
the recorded body prediction error.

Using the existing D-013T route-cost model:

- tick 388: support upper bound 28.1601, energy 0.1565, reserve 0.1065, route
  cost 0.1060 — feasible;
- tick 389: support upper bound 29.1322, energy 0.1525, reserve 0.1025, route
  cost 0.1120 — infeasible.

This proves a genuine support-bounded recoverable-to-unrecoverable transition
without using hidden habitat truth.

## Correction retained

The correction keeps nominal estimates, generic confidence/uncertainty, and
unitful support separate. Direct internal sensor observations publish the
declared sensor support. WorldModel entities carry optional support; verified
body-relative motion propagates remembered nominal state and grows the support
envelope. Incompatible remembered re-identification invalidates the support.
Only remembered entities with justified support are returned to policy. The
existing arbitrator route budget uses the support upper bound, and its bounded
`preserve_recoverability` guard activates only on a projected
feasible-to-infeasible transition.

No absolute coordinates, generic uncertainty reinterpretation, new estimator
framework, new planner, fixed energy threshold, outcome-effect change,
evaluator change, or V2 change was introduced.

## Runtime proof

The main S0-like continuation ran 500 ticks with verified identity, governance,
and persistence. It recorded 13 verified charges and diverse non-energy action,
but minimum energy was 0.0 and the critical boundary was crossed. The abundant
control also retained action diversity and no continuous charge loop, but it
likewise crossed critical energy. The runtime proof therefore did not satisfy
the D-013V PASS sequence.

## Validation and integrity

D-013V focused tests: 7 passed. The combined D-013 family set passed 34 tests.
The final full suite passed 786 tests with 2 skips and 2 environment warnings.
D-009 and D-010 evidence validators passed; governance validation passed in
ADOPTED mode. The D-010 runtime-tick inventory was re-anchored to current
source line locations only; D-010 thresholds, raw ledger, measurements, and
performance verdict were not changed.

No formal P0 was launched. No formal tag was created. D-013S/D-013T-R1 and
other historical evidence, thresholds, verdicts, `.agent/RECORD.md`, and
`.agent/LIBRARY_REVIEW.md` were preserved.
