# UMBRA-D-013J — V2 Formal Runner Entrypoint Contract Correction

Status: `D013J_V2_RUNNER_ENTRYPOINT_CORRECTION_PASS`

This dossier records the narrow runner-boundary correction authorized by
UMBRA-D-013J. The correction makes the existing V2 formal runner CLI usable
without changing the V2 contract, configuration fingerprint, worker, organism
code, formal evidence, or formal-run authority.

## Root cause

`experiments/d012/run_formal_p0.run()` already required four V2 trace paths,
but `main()` exposed no trace-path arguments and called `run()` without a
mapping. A normal V2 CLI invocation therefore failed closed before the worker
could be launched.

## Correction

When `recovery_contract_version` is V2 and `formal_trace_paths` is omitted,
the runner now selects these deterministic paths under `<run_root>/evidence/`:

- `PHYSIOLOGY_TRACE.jsonl`
- `RECOVERY_TRACE.jsonl`
- `FIRST_FAILURE.json`
- `P0_RECOVERY_EVALUATION_TRACE.jsonl`

A complete explicit V2 mapping remains honored. A partial explicit V2 mapping
continues to fail closed. V1 behavior remains unchanged.

The focused CLI test intercepts `WorkerClient.launch`, verifies the complete
manifest at the worker boundary, and verifies exactly one `EVALUATOR_INIT`
record in the evaluation trace. No formal P0 execution was authorized or
launched by D-013J.

## Scope boundary

Changed files are limited to the runner boundary, its focused regression
tests, and this documentation dossier. `umbra_core/`, experiments other than
the runner boundary, historical evidence, D-013I evidence, formal
configuration, protected governance files, and formal tags were not modified.

`next_phase_authorized: false`
