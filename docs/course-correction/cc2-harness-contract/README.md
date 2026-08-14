# UMBRA-CC-002 read-only harness contract

Status: `RESEARCH_ONLY`, `NON_QUALIFYING`, `NOT_FORMAL_EVIDENCE`.

This prototype validates an explicit experiment boundary around the existing
D-009 qualified `C0/S0` route. It does not modify `umbra_core/`, D-009
preregistration, sealed evidence, thresholds, verdicts, or production authority.

The bounded subject uses seed `7` and a 40-tick research window, while the
canonical D-009 S0 definition remains 2,400 ticks. The bounded run is not a
qualification rerun. The reference route is the existing
`experiments/d009/run_experiment.py::_run_integrated_trace`; the shadow route
constructs the same production organism and invokes `Organism.tick_once`
directly behind contract boundaries.

Results: exact deterministic equivalence for the declared comparison fields and
10/10 fail-closed fault injections. The only observed divergence was resolved
by reproducing the existing C0/S0 metric-collector convention explicitly.
