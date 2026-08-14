# Metric contract

The selected bounded subject compares only deterministic fields exposed by the
existing D-009 route: tick budget, action count, manipulation counts, governed
alignment, verified alignment, effect count, unauthorized habitat changes,
prediction hits/total, object and zone bounds, and boundedness.

Sources are `Organism.tick_once`, `HabitatEngine.snapshot_view`, and the
existing D-009 world-model prediction ledger. Units are ticks, counts, hashes,
and dimensionless rates. Missing fields are a contract failure, not zero-filled
evidence. The existing C0/S0 baseline convention that sets
`governed_alignments=1` is reproduced explicitly and documented as a collector
rule. Metrics are diagnostic for CC-2 and never verdict-bearing.
