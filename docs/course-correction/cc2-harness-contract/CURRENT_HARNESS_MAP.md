# Current D-009 harness map

## Selected boundary

- Canonical scenario: `experiments/d009/scenario-suite.json`, `S0`,
  `baseline_autonomous_habitat`, canonical budget 2,400 ticks.
- Canonical condition: `C0`, full persistent habitat and environmental agency.
- CC-2 subject: the same `C0/S0` boundary, seed 7, bounded 40-tick window,
  explicitly non-qualifying and isolated from `docs/evidence/d009/`.

## Actual execution path

1. `experiments/d009/run_experiment.py::_build_jobs` expands frozen matrix
   cells and paired seeds; `_cell_worker` owns one disposable temporary DB.
2. `_run_integrated_trace` calls `_organism_cfg`, which creates an
   `OrganismConfig` with seed, condition, scenario, enabled production modules,
   habitat hook, body profile, and a disposable DB path.
3. `umbra_core.runtime.create_organism` constructs the organism and its
   persistent store. The route attaches a `HabitatEngine` built from
   `_habitat_state_for_scenario`, then attaches it to the embodiment.
4. `Organism.tick_once` is the execution entrypoint. The route observes
   capability, denial, outcome, habitat hashes, prediction errors, object and
   zone bounds, and routine/replay-specific state.
5. `experiments/d009/evidence.py` supplies frozen-hash preflight, metric
   envelopes, raw-row construction, raw-ledger writing, and seed-manifest
   writing. `run_all` aggregates per-gate results with `ev.comparison`.
6. `experiments/d009/validate_evidence.py` reloads raw rows and result files,
   recomputes metrics/comparisons, checks hashes, coverage, fields, and claims.
7. The formal D-009 verdict is historical sealed output. CC-2 does not call
   `run_seal`, write formal evidence, or issue a qualification verdict.
8. Cleanup is `Organism.close`, temporary DB cleanup, and worker process exit.

## Boundary notes

Seed enters `OrganismConfig(seed=seed)` and the organism RNG. S0 has no scenario
plant. Controls and ablations exist in the frozen D-009 matrix, but are not
silently included in this C0/S0 subject. Restart/replay behavior is mapped in
the existing S10/S11 branches but is out of scope for this bounded first
contract subject.
