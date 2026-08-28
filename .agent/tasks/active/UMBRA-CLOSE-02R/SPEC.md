# Scope

Replace the CLOSE-02 flat additional_candidates architecture with a
source-neutral hierarchy: native higher-level intents are admitted first;
the existing low-level Arbitrator selects once among valid intent-backed
actions; hard authority constraints, Governance, Embodiment, and
VerifiedOutcome remain unchanged.

Urgent recovery bypasses optional intents. No valid intent preserves the base
candidate path. Invalid intents fall back to the established safe base pool.
Equivalent behavioral intents are deduplicated without provenance weighting;
source collection order cannot affect behavior or RNG assignment.

Forbidden: serial overwrite restoration, planner/search, source priority or
weights, threshold/effect changes, hidden truth, H3/D-013/AX, storage work,
retry, reseed, and automatic successor generation.
