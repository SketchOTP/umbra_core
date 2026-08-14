# UMBRA-CC-003 Restart / Replay Contract

This dossier records a `RESEARCH_ONLY`, `NON_QUALIFYING`, `NOT_FORMAL_EVIDENCE`
validation of the existing D-009 `C0/S10` restart boundary. It uses the real
`_run_integrated_trace` route and an isolated shadow route. It does not write
`docs/evidence/d009/` or any other canonical evidence directory.

The selected subject is S10 (`restart_during_manipulation`): the qualified
route snapshots at tick 35, cleanly closes, reloads the same database through
`load_organism`, reconstructs C0 habitat from the saved authoritative state,
and continues to tick 80. S11 only snapshots without the required reload /
continued-execution boundary and is not the smallest complete subject.

Result: exact deterministic equivalence for the declared fields and 21/21
fail-closed restart, metric-continuity, and evidence-isolation fault
injections, with zero silent failures. The 15 required restart faults were
supplemented by five metric-continuity faults and one canonical-path fault.

Only clean close/restart is exercised. Controlled interruption and unexpected
crash recovery are `NOT_EXERCISED`.
