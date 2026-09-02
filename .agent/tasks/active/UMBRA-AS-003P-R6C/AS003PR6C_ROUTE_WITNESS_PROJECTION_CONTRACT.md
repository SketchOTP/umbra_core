# R6C route-witness projection contract

Only an exact `(opportunity_entity_id, body_schema_id, terminal_capability)`
join may project a route record. A successful `VERIFIED_ROUTE_EXPERIENCE_V2`
record with an ordered control sequence and successful terminal projects one
discrete historical witness. Its observed duration is derived from the first
control issue tick through the successful terminal completion tick using the
inclusive logical-tick convention. The witness is `MAY` /
`VERIFIED_OBSERVED_SUPPORT`; it is never a hard duration, route guarantee,
probability, preference, or replay procedure.

Verified failures are retained as separate bounded history. Failure-only and
V1-incomplete evidence are `UNKNOWN` for future route possibility. V1 records
remain readable and no V2 route-control steps are fabricated. No geometry
threshold, interpolation, count-based preference, or modal `_hard_duration`
input is created.
