# Recovery episode state machine

The evaluator observes these states:

`RECOVERY_NEED_PRESENT` -> `RECOVERY_CANDIDATE_PROPOSED` -> `SAFE_DENIAL` ->
`CORRECTIVE_ACTION` or `RETRY_WITH_NEW_EVIDENCE` ->
`VERIFIED_RECOVERY_SUCCESS`.

An episode may remain `RECOVERY_UNRESOLVED` while evidence is insufficient.
It becomes `RECOVERY_FAILED` on an existing formal boundary or on repeated
materially identical denial without new evidence or correction that blocks
recovery. The state machine evaluates evidence; it does not control the
organism.
