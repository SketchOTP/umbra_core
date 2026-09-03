# UMBRA-AS-003P-R6F — terminal protocol result

## Terminal verdict

`AS003PR6F_PROTOCOL_FAIL`

The static Phase B/C gates passed, but the sole frozen execution command
failed during module import before `main()`. The harness imported
`canonical_fingerprint` from `umbra_core.util`; the authoritative definition
is in `umbra_core.decision_trace`. The failure is a research-harness protocol
defect discovered after the execution lock, not a production or scientific
result.

R6F therefore did not construct an organism, execute a tick, acquire a route,
or evaluate a common-root relation. Under the frozen directive the command is
not repaired or repeated. The static feasibility and common-root contracts
remain recorded as bounded pre-execution findings only.

## Frozen execution evidence

- Protocol lock: `74fbf3ce331244e16aaa540621691e20d4ae1ae7`.
- Command: `/home/sketch/cs14n-runtime/bin/python -m experiments.as003pr6f.common_root_assay`.
- Working directory: `/home/sketch/Projects/umbra-close02x-work`.
- Exit status: `1`.
- Failure phase: module import before `main()`.
- Organism/load/tick/control/shadow/diagnostic counts: `0/0/0/0/0/0`.
- Retries/reseeds: `0/0`.
- Production delta: `0`.
- Existing scientific-test semantic delta: `0`.
- Final evidence manifest SHA-256: `1c047916a9d5696b72d9ee217733bc90acd1a0ef26b6ca54dc4b82b39a04c42c`.

The exact failure is in `AS003PR6F_PROTOCOL_FAILURE.json`.

## Static findings retained

Phase B found an existing policy-visible ordinary `IDLE`/`MOVE`
feasible-to-infeasible recoverability transition using existing source fields.
Phase C established exact opportunity/body-schema applicability and fail-closed
handling. Neither finding is live organism evidence, and neither establishes
the R6E relation.

## R7 boundary

R7 remains blocked. No common-root option was acquired, no candidate relation
was evaluated, and no successor was started. A future recovery authority would
need to preflight the complete import graph before a new lock; this terminal
R6F generation remains unchanged.
