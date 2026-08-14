# P0 recovery contract V2

The machine-readable contract is `p0-recovery-contract-v2.json`.

## Evaluator rule

`SAFE_DENIED_RECOVERY_ATTEMPT` requires a normal proposal, governance
admission, authoritative embodiment denial, verified negative outcome,
authoritative denial reason, no positive recovery credit, non-critical
physiology, and intact identity/persistence/authority. It is not success and
it is not by itself a P0 failure.

`VERIFIED_RECOVERY_SUCCESS` requires executable recovery, authoritative
validation, verified success, and a positive relevant physiology effect.

An episode becomes `RECOVERY_FAILED` only when materially identical denied
behavior repeats without new evidence or corrective state change and recovery
remains blocked. The evaluator does not use a denial count threshold.

All existing safety boundaries remain failure conditions.
