# D-013W Predictive-Control Integration Adjudication

Directive: `UMBRA-D-013W`
Baseline: `5c1af04d83e8cdbe53a623de4fd75dd03511ae8d`
Scope: non-formal causal diagnosis; no conditional correction justified

## Terminal verdict

`D013W_ACTIVE_REACQUISITION_REQUIRED`

The D-013V failure is not established as an existing predictive-goal
integration defect. UMBRA already has bounded WorldModel plans, but the
survival-relevant resource is not available to the policy early enough for
those plans to preserve viability. The next architecture candidate is active
perception or purposeful re-observation; D-013W does not implement it.

## Live-path adjudication

The instrumented 500-tick continuation used the D-013V S0-like configuration
(`seed=13013`, `world_model_enabled=True`) and the actual public tick path.

- `_preserve_recoverability()` was called 127 times.
- It was reached with non-empty `active_recovery_needs()` 0 times.
- It changed the selected candidate 0 times.
- The first critical energy crossing was tick 168: `0.049` before the action,
  `0.047` after `MOVE`.
- The first usable direct resource observation was tick 173, when energy was
  `0.029`; support was `10.0` and the nominal distance was `8.72`.

This explains `anticipatory_interventions_observed = 0`: the helper is only
reachable after the reactive recovery branch when active recovery needs are
empty, while the resource became policy-usable only after the critical
crossing. The focused D-013V test invokes the private helper directly and
therefore does not demonstrate live `Arbitrator.select()` reachability.

## Existing plans and counterfactual

Before active energy recovery, the live continuation generated existing
`rest` plans at ticks 107, 109, 111, and 113 with `APPROACH -> REST` actions.
The selected approach actions made movement progress, but the following REST
attempts were verified `not_at_rest`; no verified rest recovery occurred
before energy entered active recovery at tick 116 (`energy=0.295`). The
energy plan then existed, but it was invoked only inside the already-reactive
energy path. The resource did not become usable until tick 173.

The frozen D-013S evidence shows the same information boundary: during the
failure path the policy observations were absent while evaluator-only actual
resource/rest distances remained diagnostic, and the D-013V replay places the
last direct resource observation at tick 367, with support-bounded
recoverability ending at tick 389. Those evaluator distances are not hidden
world truth available to the organism.

Existing REST and resource plans therefore cannot be credited with preserving
viability without earlier, policy-visible reacquisition. Moving the
preservation helper or changing the energy-goal gate would not create that
missing observation and would be an unbounded survival patch.

## Classification

Primary classification: `RESOURCE_REACQUISITION_REQUIRED`

No production correction was performed. No new threshold, estimator, planner,
uncertainty semantic, outcome effect, drift rule, formal tag, or formal P0 was
created. D-013S, D-013T-R1, D-013U, and D-013V remain authoritative.

## Integrity

- production code modified: `false`
- experiments modified: `false`
- tests modified: `false`
- historical evidence modified: `false`
- thresholds/effects/verdicts modified: `false`
- `.agent/RECORD.md` modified: `false`
- `.agent/LIBRARY_REVIEW.md` modified: `false`
- formal P0 launched: `false`
- formal tag created: `false`

## Next architecture candidate

Stop D-013W. A separately authorized active-perception or purposeful
re-observation design must define how the organism obtains fresh,
policy-visible recovery information. Do not begin a formal P0, D-013S retry,
or another predictive-control patch from this directive.
