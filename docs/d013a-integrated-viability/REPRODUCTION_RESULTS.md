# Reproduction Results

Pre-correction focused test: failed (`MOVE` instead of `APPROACH`).

Post-correction focused test: passed.

Post-correction bounded `run_energy_reproductions.py --root /tmp/d013a-post`:

- R0 exact failed configuration: tick 191, energy `0.2065`, critical `false`.
- R1 cleanup-disabled: tick 191, energy `0.2065`, critical `false`.
- R2 reachable recovery: tick 191, energy `0.2330`, critical `false`.
- R3 D-009 baseline: tick 191, energy `0.2065`, critical `false`.
- `formal_relaunch: false`.
