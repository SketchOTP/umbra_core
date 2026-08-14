# Persistence Contract

The harness observes the existing SQLite path. `Organism.snapshot_if_due`
writes a verified snapshot with the current event sequence and authoritative
state. `Organism.close` closes the same `Store`; `load_organism` reloads the
identity and latest snapshot, verifies snapshot identity, restores physiology,
embodiment, governance, seed/RNG state, and then the D-009 C0 habitat recovery
function restores the persisted habitat state. CC-3 does not substitute mock
persistence.
