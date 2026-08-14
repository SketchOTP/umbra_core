# Root-cause adjudication

Primary class: `J_SIGNAL_DURING_TICK_ATOMICITY_DEFECT`.

This is an implementation defect, not a test defect. The test exercised a legitimate ordinary termination during active work. The implementation allowed an authoritative event row and its ledger-tip pointer to become durably inconsistent. Ownership protections, identity semantics, SQLite integrity, and replay validation were not the cause.
