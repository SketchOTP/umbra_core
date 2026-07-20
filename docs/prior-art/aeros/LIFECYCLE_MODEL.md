# Lifecycle model

Signed transitions required for: birth, operator transfer, body bind/unbind, migration export/import, capability state changes.

Capability states: DISCOVERED → QUARANTINED → VALIDATED → SHADOW → CANARY → ACTIVE (no DISCOVERED→ACTIVE jump).

Authority changes cannot occur via memory, learned policy, model output, capability package, or body adapter.
