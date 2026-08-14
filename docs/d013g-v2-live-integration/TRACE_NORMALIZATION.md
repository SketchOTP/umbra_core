# Trace normalization

`experiments/d012/formal_contract_v2.py::normalize_trace_row()` derives V2 facts from actual worker rows.

The observation signature hashes sorted policy-visible fields: observation ID, observed time, kind, estimated distance, confidence, uncertainty, and perception-state version where present. Authoritative coordinates are excluded.

`new_evidence` is true for the first observation or a changed signature. `corrective_action` is true only for a verified successful `APPROACH`, `ORIENT`, or `MOVE`. `recovery_blocked` is derived from a CHARGE candidate with no chargeable executable affordance. Actual resource distance and the existing execution boundary are copied from recorded affordances only for integrity checking.

The live worker supplies these facts. Explicit fields remain accepted for frozen fixtures and historical replay tests.
