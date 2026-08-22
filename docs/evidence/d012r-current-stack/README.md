# D-012R current-stack integrated viability recheck

Terminal verdict: `D012R_HISTORICAL_D012_PHENOTYPE_NOT_REPRODUCED_CURRENT`

This bounded non-formal recheck ran matched current-stack conditions from
baseline `90dc9b939e6128b80641cab5c91aa926336451f1`:

- L1/L2: D-010 disabled
- T1/T2: D-010 enabled
- seed `12012`, S2 habitat, event-0 prefix, maximum 400 logical ticks
- four cases, zero retries, zero production changes

All four cases completed 400 ticks without critical physiology failure. L1/L2
and T1/T2 reproduced their selected-action and physiology paths. L and T had a
common 400-tick behavioral/physiology prefix; T contained temporal state but no
observed action or physiology divergence in this bounded window.

The historical D-012B2 tick-181 collapse was not reproduced on the current
stack. Historical energy crossed `0.0525 -> 0.0485` after `MOVE` with resource
distance `3.8042`; current L at tick 181 had energy `0.6075`, selected
`ORIENT`, and resource distance `0.2610` (executable). The first material H→L
divergence was tick 34. This does not qualify integrated viability or authorize
a formal P0.

Full evidence is stored on the attached volume:

`/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d012r-current-stack-viability-r1/`
