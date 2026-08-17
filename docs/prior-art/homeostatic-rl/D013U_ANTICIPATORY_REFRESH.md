# D-013U Anticipatory Viability Refresh

Directive: UMBRA-D-013U
Baseline: `89801993a893a94ba6c17160fdd584aa457b108f`
Scope: architecture audit and bounded non-formal correction decision
Date: 2026-08-16

## Decision

`D013U_UNCERTAINTY_MODEL_INSUFFICIENT`

No production correction is retained from this directive. No formal P0, formal
tag, D-013S retry, threshold change, outcome-effect change, evaluator change, or
historical-evidence change was made.

## Existing architecture audit

The live WorldModel is enabled in the D-012 worker and uses bounded planning
with maximum plan depth 4. Its energy plan composes existing
`APPROACH -> CHARGE` actions and records learned entities with estimated
distance, confidence, uncertainty, and fact kind. Runtime planning becomes
influential only after energy urgency exceeds the existing reactive trigger;
this is an emergency/recovery trigger, not a prospective viability guard.

The D-013S trace shows that the resource was directly observed by policy through
approximately tick 367, with the last sensor observation timestamp at tick
356. At tick 367 the remembered estimate was approximately distance 9.819,
confidence 0.3949, and uncertainty 0.6051, while energy was approximately
0.2695. The resource then disappeared from ordinary policy observations through
tick 408. At tick 409 it reappeared at estimated distance 9.304 while energy
was approximately 0.0725; the existing bounded route cost then exceeded the
remaining reserve. The formal failure followed at tick 414.

This establishes that the resource was legitimately known earlier, but it does
not establish a robust distance bound for the stale estimate.

## Uncertainty finding

Perception defines uncertainty as `1 - confidence` after sensor confidence is
derived from range and noise. It is not documented or represented as a
distance standard deviation, interval, or calibrated positional error. The
WorldModel persists that value as an uncertainty score and increases it during
persistence decay.

The proposed viability calculation requires a conservative projected
resource-distance bound. Converting the existing uncertainty score into extra
distance would invent semantics. Using the point estimate without an
uncertainty allowance would not be a robust prospective feasibility result.
Therefore the authorized correction stops at the explicit D-013U uncertainty
gate.

## Prior-art refresh disposition

- Keramati and Gutkin, *Homeostatic reinforcement learning for integrating
  reward collection and physiological stability*: ADAPT as bounded
  drive/anticipation context; not a production controller.
- Continuous HRRL: REFERENCE/ADAPT for anticipatory regulation; no direct
  runtime adoption.
- Yoshida homeostatic agents and nutritional homeostatic RL repositories:
  REFERENCE for mechanism equations and controls; upstream runtime stacks are
  not production dependencies.
- Existing UMBRA WorldModel, vector physiology, D-013T route budget, verified
  outcomes, and policy-visible observations: REUSE candidates, but route
  robustness remains unresolved until uncertainty semantics are extended by a
  separately authorized architecture directive.

Sources and pinned dispositions remain in `SOURCES.md`,
`MECHANISM_MATRIX.md`, `FORMAL_MODEL.md`, and `COMPANION_RELEVANCE.md`.
No external production code was adopted.

## Integrity

- production code modified: false (trial edits removed before closeout)
- tests modified: false (trial test removed before closeout)
- D-013S evidence modified: false
- D-013T-R1 evidence modified: false
- historical evidence/verdicts/thresholds modified: false
- formal P0 launched: false
- formal tag created: false
- `.agent/RECORD.md`: unchanged
- `.agent/LIBRARY_REVIEW.md`: preserved
