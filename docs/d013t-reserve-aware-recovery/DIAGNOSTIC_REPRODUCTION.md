# D-013S failure reproduction

The frozen D-013S FIRST_FAILURE.json is the authoritative reproduction of the
tick-414 state:

- energy before APPROACH: 0.0525
- policy-visible estimated resource distance: 5.011992881370536
- selected, governed, executed, and verified capability: APPROACH
- verified APPROACH energy effect: -0.004
- predicted/observed energy after action: 0.0485
- critical energy floor: 0.05
- resource was not executable

The correction tests reproduce the same physiology boundary on the real
Arbitrator path before any formal execution. The unsafe APPROACH is now
classified as unsafe and the route is exposed as energy-recovery-route
infeasible through the existing SIGNAL_ASSISTANCE capability.
