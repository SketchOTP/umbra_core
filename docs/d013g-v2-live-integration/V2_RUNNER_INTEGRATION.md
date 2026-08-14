# V2 runner integration

`organism_worker.py::run_formal_tick()` keeps the V1 branch unchanged. Under V2 it appends the recovery row, evaluates the live episode, and writes `P0_RECOVERY_EVALUATION_TRACE.jsonl`.

`run_formal_p0.py::sample()` uses the selected contract at the formal-failure boundary. A legacy safe-denial failure is ignored only when V2 independently classifies its triggering row as `SAFE_DENIED_RECOVERY_ATTEMPT`; all other failure records remain fail-closed.

The runner also connects V2 closeout to `validate_read_only()` after worker shutdown and records `P0_READONLY_POSTRUN_VALIDATION.json`.
