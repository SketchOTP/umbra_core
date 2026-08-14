# Real production-path proof

The shadow executor asserts at runtime that:

- `create_organism` resolves to `umbra_core/runtime.py`;
- the constructed organism's `tick_once` resolves to `umbra_core/runtime.py`;
- `HabitatEngine` resolves to `umbra_core/habitat/engine.py`.

The reference record additionally names the existing
`experiments/d009/run_experiment.py::_run_integrated_trace` route. A substituted
legacy helper, mock organism, synthetic metric source, or wrong source path is
rejected. The generated equivalence JSON records both route descriptions and
the resolved source paths.
