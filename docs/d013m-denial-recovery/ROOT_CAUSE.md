# UMBRA-D-013M root-cause record

## Symptom

D-013L tick 138 produced a verified `CHARGE` denial with reason
`not_at_resource`. At tick 139, with no corrective movement or materially new
evidence, the organism selected `CHARGE` again.

## Root cause

The verified outcome path reached `Runtime._finish_outcome`, which called
`Arbitrator.note_outcome`. That method incremented the capability-level
`retry_counts`, but it discarded the verified denial reason and target.

The critical-energy branch in `Arbitrator.select` bypassed general candidate
scoring and returned `CHARGE` directly whenever perceived resource distance
was at most `1.5`. That branch did not consult `retry_counts`, so the verified
negative outcome had no causal effect on the next recovery decision.

The deterministic pre-fix reproduction was:

```text
first: CHARGE
retry_counts: {'CHARGE': 1}
second: CHARGE
```

## Correction

The arbitration state now retains one bounded, serialized verified denial for
`not_at_resource`, `not_at_affordance`, or `not_executable`, including the
capability and recovery target. The runtime supplies that information from the
verified outcome and pending action parameters.

When the same recovery target is immediately denied, the energy recovery
branch selects `APPROACH` instead of repeating `CHARGE`. A subsequent verified
corrective outcome clears the denial state, allowing a later executable charge
opportunity. Physiology remains changed only by verified outcome effects, so a
denied charge receives no positive energy credit.

This is a non-formal organism correction. It does not change the V2 contract,
formal thresholds, D-013L evidence, historical evidence, or any formal tag.
