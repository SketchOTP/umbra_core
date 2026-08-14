# Independent Review

Read-only review scope: real restart route, production recovery path, state
comparison, segment IDs, metric boundary, fault coverage, evidence isolation,
and D-010 non-implication.

Review checks passed: S10 is a real clean close/reload/continue path; the
shadow calls production `create_organism`, `load_organism`, `Organism.tick_once`,
`Store`, and `HabitatEngine`; comparison is against the independent reference
route; segment IDs and one-execution relationship are explicit; metric
continuity has dedicated duplicate/mixing/denominator/segment faults; the
canonical evidence path is rejected; and no production, historical, D-010, or
sealed-evidence path is modified. A preliminary read-only observation found
generic detector labels for provenance faults; those labels were tightened in
the separate correction commit and the full harness rerun passed 21/21.

The review found no Critical or Important findings after correction.

Verdict: `APPROVE_WITHOUT_CRITICAL_OR_IMPORTANT_FINDINGS`.

Limit retained: this validates only clean close/restart for D-009 C0/S10. It
does not test controlled interruption or unexpected crash recovery and says
nothing about D-010 performance or qualification.
