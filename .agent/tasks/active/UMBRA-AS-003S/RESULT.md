# Result

Terminal verdict: `AS003S_ATOMIC_BODY_REPLACEMENT_IDENTITY_QUALIFIED`.

AS-003S adds a dedicated `embodiment_body_replaced` event and one local SQLite
transaction that commits that event with its matching prospective full snapshot.
No live owner changes before commit. On success, the constitutional organism is
unchanged while the physical body ID, active SelfModel binding/schema, and coherent
EmbodimentAdapter/Embodiment occupancy change together.

The retained bounded lifecycle changed body
`370779a8-9e33-476a-9ea4-127eb243e037` to
`e5a6897b-48e9-489d-b681-7628b21099c6`, generation `1` to `2`, binding
`f68932c7-1e5c-ca6f-369e-60882b0bfa88` to
`5331c65d-285d-7aac-ba06-31f62dc8bfa0`, and schema
`aa0aceed-956a-ba3b-661d-fd1ef99338b3` to
`1291277f-ba1c-82f9-50ab-45902cdafaeb`. Agent and lineage ID remained
`bb7cc68a-9436-bc95-ed21-0677f19fe0f4`.

Focused proofs passed `14/14`. Crash-before-commit stages roll back event and
snapshot; committed-before-live-apply recovers exactly once on restart. Old
generation references fail closed. Pending execution and old-body held objects
reject replacement. Compatible profile swap retains the body instance and remains
semantically distinct. All D-008 tests pass; observed D-002/D-009 failures are exact
baseline reproductions, and the path-safe applicable suite has no candidate-only
failure. Authority 3.0 and governance pass. One bounded organism creation and one
restart load occurred; organism ticks, observer runs, integrated viability runs,
qualification retries, and reseeds are all zero.

Recommendation only: `UMBRA-AS-003P-R5 — Prelocked Common-Root Modal Observer Pair
Candidate`. No successor started.

Final evidence manifest SHA-256:
`6aaea514b0c829ca95b78ce76f440833f24ac30e61a6f4eab7ff7affa5d203bd`.
