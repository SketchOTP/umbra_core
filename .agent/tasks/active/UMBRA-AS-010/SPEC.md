# UMBRA-AS-010 — full-configuration integrated qualification

Architect authority: `UMBRA-AS-010` from exact baseline
`b5c7bb2b46e9355a8f5b658f25ebf4f1e7fea27b`.

AS-009 remains permanently terminal as `AS009_PROTOCOL_FAIL`. Its R2/R3
results are valid reduced-configuration evidence only; AS-007 A/B/known-R1
remain valid full-configuration bounded evidence. AS-010 must reproduce the
AS-007 full runtime configuration, migrate the repaired HabitatEngine R2
perturbation, use fresh disjoint R0–R3 seeds, and run the downstream
qualification chain without modifying `umbra_core/**`.

After scientific lock, no harness repair, retry, reseed, or threshold change
is permitted. CLOSE-03 remains blocked unless every AS-010 gate qualifies.
