# Current D-009 Restart Map

| Responsibility | Actual route |
|---|---|
| Definition / scenario | `experiments/d009/scenario-suite.json:S10`; `run_experiment.py::tick_budget` |
| Pre-restart construction | `experiments/d009/run_experiment.py::_run_integrated_trace` -> `umbra_core.runtime.create_organism` |
| Database | `run_experiment.py::_organism_cfg` -> `umbra_core.persistence.Store` |
| Event ledger | `umbra_core.persistence.Store::append_event`, `last_sequence`, `last_event_hash`, `iter_events` |
| Snapshot | `umbra_core.runtime.Organism::snapshot_if_due` -> `Store::save_snapshot` |
| Identity / birth commitment | `Store::save_identity`, `Store::load_identity`, `umbra_core.identity::verify_identity` |
| Habitat persistence | `run_experiment.py::_habitat_engine_after_restart`; C0 restores `saved_state` |
| Tick / RNG | `Organism.tick_once`; `load_organism` restores `state.seed` and `state.rng_state` |
| Close | `umbra_core.runtime.Organism::close` -> `Store::close` |
| Recovery | `umbra_core.runtime.load_organism` loads identity and latest verified snapshot |
| Post-restart construction | `load_organism` plus D-009 `_habitat_engine_after_restart` and `HabitatEngine` attach |
| Continuity | identity, identity commitment, event sequence/hash chain, snapshot state, habitat hash, final outcome |
| Cleanup | CC-3 uses a temporary directory under the research harness; canonical evidence is forbidden |

The route is a clean close/restart. No crash injection or process-kill path is
claimed. `jCodemunch-MCP` was unavailable; this map was established by
narrowly targeted read-only source inspection and runtime source-path proof.
