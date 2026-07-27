# UMBRA-D-012B1 Root-Cause Verdict

## Verdict

`UMBRA_D012B1_INTEGRATION_DEFECT_CONFIRMED`

Remediation: `REMEDIATED_AND_REVALIDATED`

Primary classification: `ARBITRATION_OR_GOVERNANCE_RECOVERY_FAILURE`

## Finding

The organism was already critical before cleanup. Energy first fell below the
0.05 bound after tick 181 and reached 0.0015 at tick 191. R1 reproduced the
same tick, energy, identity, and chain tip without quiesced cleanup, so cleanup
only observed and snapshotted the failure.

At ticks 185–191, the critical energy-recovery branch selected and governance
admitted `CHARGE`. The perceived distance at tick 185 was 1.5165, so
arbitration's `distance <= 2.2` rule stopped approach. Actual distance was
1.5259, while embodiment permits charging only through
`feature.radius + 0.3 = 1.5`. Every verified outcome therefore failed with
`not_at_resource`; the body did not move and the same failure repeated.

The formal schedule did not guarantee starvation: passive drift alone would
have left energy at 0.318 after 191 ticks. R2 remained viable when the existing
resource was confirmed executable. R3 reproduced the defect without D-011 or
D-012 supervision, locating it in qualified organism subsystem integration
rather than the formal harness.

## Remediation

The critical energy-recovery transition now continues `APPROACH` until the
perceived distance is within the existing 1.5 execution boundary. No viability,
privacy, governance, or performance threshold changed.

The remediated reproduction approached at tick 185, completed a verified
`CHARGE` at tick 186, and finished tick 191 viable at energy 0.4285.

## Boundaries

The failed formal P0 verdict and all 19 original evidence artifacts remain
unchanged. This adjudication did not relaunch formal P0 and does not authorize
formal P0, P1, P2, or D-012C.
