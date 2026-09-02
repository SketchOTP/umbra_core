# R6B evidence protocol

Evidence root:
`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r6b-verified-route-learning-r1/`

All records use atomic temporary-file replacement, file fsync, directory fsync,
and SHA-256 readback. Pure test output is retained per command. The R6A result,
R5A/R6 traces, and all historical aggregate failures are immutable inputs and are
not tuning evidence.

Required closeout records include state reconciliation, contract locks, resolver
and lifecycle proofs, persistence/provenance/isolation audits, pure test results,
both bounded assay records, body-replacement isolation, verdict, and final
manifest.
