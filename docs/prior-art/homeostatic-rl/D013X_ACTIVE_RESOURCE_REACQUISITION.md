# D-013X Purposeful Active Resource Reacquisition

Directive: `UMBRA-D-013X`
Baseline: `423a661acaabfb393fc005d98933ee12cdda0219`
Scope: non-formal architecture gate; no reacquisition correction justified

## Terminal verdict

`D013X_REACQUISITION_MEMORY_INSUFFICIENT`

The required remembered resource cue does not survive into the active energy
recovery window before critical failure. No active-perception behavior was
implemented because there is no policy-safe memory signal around which to
build it.

## D-013W causal reproduction

The same D-013W live public tick path was run for 500 ticks with
`seed=13013` and `world_model_enabled=True`.

- active energy recovery began at tick 116, energy `0.295`;
- the first critical crossing occurred at tick 168, energy `0.049` before
  `MOVE` and `0.047` after;
- the first direct `CURRENT_OBSERVATION` for a resource arrived at tick 173,
  energy approximately `0.029`, nominal distance `8.72`, support `10.0`;
- the first policy-visible `REMEMBERED_ESTIMATE` resource cue arrived only at
  tick 223;
- no remembered resource cue was available to policy at any tick through the
  critical crossing.

The exact cause is memory absence at the required boundary: no resource
entity existed in the policy-visible WorldModel path before the first direct
resource observation. The later remembered cue cannot support reacquisition
before the earlier failure.

## Architecture gate

`remembered_resource_present_before_critical: false`

The active-perception sequence cannot be tested honestly on this trajectory:

`remembered resource -> ORIENT/MOVE -> fresh observation`

would require inventing a cue that the organism did not possess. No remembered
estimate was treated as a current observation, no hidden coordinates or
evaluator truth were exposed, and no CHARGE was credited from memory.

## Integrity

- production code modified: `false`
- experiments modified: `false`
- tests modified: `false`
- thresholds/effects/drift modified: `false`
- historical evidence modified: `false`
- `.agent/RECORD.md` modified: `false`
- `.agent/LIBRARY_REVIEW.md` modified: `false`
- formal P0 launched: `false`
- formal tag created: `false`

## Stop condition

D-013X stops at the memory gate. The next architecture decision must address
how a policy-safe resource memory cue is established or preserved before the
recovery window. Do not implement search behavior around nonexistent memory,
start a formal P0, or retry D-013S from this directive.
