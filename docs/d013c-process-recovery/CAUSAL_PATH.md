# Causal path

`SIGTERM during active tick` → `append_event INSERT events` → process death before the separate `ledger_tip` update → valid event row with stale ledger tip → generation-2 ownership reclaim succeeds → `load_organism` validates the chain → `ledger_tip_mismatch` → startup exit 1.
