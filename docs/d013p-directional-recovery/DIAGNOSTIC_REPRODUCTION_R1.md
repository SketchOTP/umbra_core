# D-013P-R1 Diagnostic Reproduction

The committed D-013P source used:

    phys.active_recovery_needs() or phys.needs_recovery()

The three deterministic sole diagnostic-only cases reproduced the review
finding:

| case | needs_recovery | active_recovery_needs | recovery_focus | selected action |
| --- | --- | --- | --- | --- |
| high integrity only | integrity | [] | integrity | REST |
| high energy only | energy | [] | energy | CHARGE |
| low fatigue only | fatigue | [] | fatigue | REST |

The reproduction used otherwise viable physiology, one relevant nearby
affordance, no drift, tick 100, and seeded RNG 13013.

The diagnosis was therefore causally reproduced before correction.
