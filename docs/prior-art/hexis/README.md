# Hexis prior-art — UMBRA-D-000 Track 3

Independent evaluation of QuixiAI/Hexis for **durable continuity and memory architecture**, not as the UMBRA creature brain.

## Pin

See `SOURCES.md` and `docs/evidence/d000-track3/source-manifest.json`.

## What was done

1. Upstream Postgres brain image built; migrations from empty volume.
2. Memory create paths exercised with a **session mock** of `get_embedding` (real embedding sidecar unavailable).
3. DB restart preserved written memories.
4. Independent SQLite reproduction of typed memory, provenance, history causality, heartbeat separation, identity layers, and safety (`independent_reproduction/`).
5. Classifications written to the selection ledger and `classifications.json`.

## Verdict (summary)

`UMBRA_D000_TRACK3_PARTIAL_MECHANISM_QUALIFICATION`

Hexis is strong prior art for transactional durable state, typed memories, provenance/revision, and restartable workers. It is **not** an organism kernel: LLM-centered heartbeat, Big Five/character-card identity, action-energy-as-metabolism, and Postgres-as-brain are rejected or referenced only.

## Non-goals

No production UMBRA core. No Hexis source vendored into product packages. No self-termination. D-001 remains blocked.
