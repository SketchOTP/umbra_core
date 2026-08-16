# D-013T-R1 extended unreachable runtime

This is a bounded non-formal real-runtime execution using the existing organism
loop and existing physiology/governance/embodiment semantics. The resource was
policy-visible but distant; no rescue, grant, teleport, threshold change, or
direct mid-run physiology write was used.

Initial state:

- seed: 13013
- body: (10.0, 3.0)
- resource: (17.0, 3.0)
- initial energy: 0.070
- critical floor: 0.050

| tick | energy before | energy after | verified outcome | denial |
|---:|---:|---:|---|---|
| 1 | 0.0700 | 0.0670 | SIGNAL_ASSISTANCE, effect -0.001 | |
| 2 | 0.0670 | 0.0650 | | signal_cooldown |
| 3 | 0.0650 | 0.0630 | | signal_cooldown |
| 4 | 0.0630 | 0.0610 | | signal_cooldown |
| 5 | 0.0610 | 0.0590 | | signal_cooldown |
| 6 | 0.0590 | 0.0570 | | signal_cooldown |
| 7 | 0.0570 | 0.0540 | SIGNAL_ASSISTANCE, effect -0.001 | |
| 8 | 0.0540 | 0.0520 | | signal_cooldown |
| 9 | 0.0520 | 0.0480 | APPROACH, effect -0.004 | |

Terminal result:

- ticks: 9
- minimum/terminal energy: 0.048
- critical boundary crossed: true
- assistance admitted: 2
- assistance denied by cooldown: 6
- verified CHARGE: 0
- route became safely feasible: false
- state-changing assistance: false
- maximum IDLE streak: 0
- fixed-action loop: false
- terminal condition: CRITICAL_PHYSIOLOGY_FAILURE

SIGNAL_ASSISTANCE emitted the existing social-signal environmental event and
its verified effect remained energy -0.001. The energy-recovery fallback did not
carry social provenance metadata that would create a partner pending episode;
no authoritative habitat mutation or energy restoration occurred. The
cooldown denials likewise had no recovery effect. The terminal approach was
observed after the organism had reached the critical boundary through the
low-reserve drift/action sequence; it was not a recovery escape.

This establishes NO_RECOVERY_PATH_AVAILABLE for the tested
tick-409-equivalent state under the existing environment and architecture.
