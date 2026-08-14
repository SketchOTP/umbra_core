# Source Path Proof

Runtime proof resolved:

- organism creation: `umbra_core/runtime.py::create_organism`
- organism recovery: `umbra_core/runtime.py::load_organism`
- ticking: `umbra_core/runtime.py::Organism.tick_once`
- persistence: `umbra_core/persistence.py::Store`
- habitat: `umbra_core/habitat/engine.py::HabitatEngine`
- reference route: `experiments/d009/run_experiment.py::_run_integrated_trace`

The shadow route imports the real D-009 configuration and production runtime
symbols. No mock persistence or synthetic replay source supplies metrics.
