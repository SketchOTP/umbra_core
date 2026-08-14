# Current D-009 Control Map

| Responsibility | Actual source |
|---|---|
| Control definitions | `experiments/d009/experiment-matrix.json`: C0 full persistent habitat; C8 habitat reset on restart |
| Qualified pair | Gate 5 cell C0/S10 versus C8/S10; `g5_c8_fail` |
| Job generation | `experiments/d009/run_experiment.py::_build_jobs` |
| Subject construction | `_cell_worker` -> `_run_integrated_trace` -> `_organism_cfg` |
| Organism creation | `umbra_core.runtime.create_organism` |
| Database ownership | `_organism_cfg` database path; `umbra_core.persistence.Store` |
| Seed pairing | `_build_jobs` uses the same seed for each matrix cell |
| Scenario/history | matrix S10 and H0; `scenario-suite.json` defines S10 and H0 |
| Metrics | `_run_integrated_trace` metrics, including `habitat_continuity_l2` |
| Raw rows | `experiments/d009/evidence.py::raw_row` and `write_raw_ledger` |
| Aggregation | `run_experiment.py::_aggregate_gate` |
| Comparison | `run_experiment.py::_aggregate_gate` calls `evidence.comparison`; frozen validator `COMPARISON_SPEC` |
| Validation | `experiments/d009/validate_evidence.py::_recompute_comparison_means` and comparison-pass checks |
| Cleanup | worker `finally` closes organism; CC-4 uses disposable research directories |

The selected pair is the smallest existing qualified comparison that has an
explicit experimental condition, explicit restart ablation, shared scenario,
shared history, and paired seed.
