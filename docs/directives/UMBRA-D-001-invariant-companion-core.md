# UMBRA-D-001 — Invariant Companion Core (Foundation)

**Status:** AUTHORIZED under `UMBRA_D000S_FOUNDATION_ARCHITECTURE_QUALIFIED`  
**Parent:** UMBRA-D-000 / UMBRA-D-000S  
**Architecture freeze:** `docs/architecture/`  
**Blocks:** production companion product features listed under Deferred

## Objective

Implement the **minimum complete organism foundation** as a clean-room Linux core that:

- persists a constitutional individual across restart;
- runs the frozen autonomous loop without user prompts or an LLM;
- regulates vector physiology with viable ranges and drift;
- perceives through a minimal embodiment membrane;
- arbitrates bounded endogenous goals;
- executes only governed primitive actions;
- records events/outcomes with deterministic replay.

## Required modules (foundation only)

1. **Constitutional identity** — agent_id, lineage, birth, lifecycle sequence, operator root, embodiment history (excludes personality/model/body/skills/mood/preferences).
2. **Persistence** — SQLite WAL event ledger + materialised state; restart continuity; deterministic replay.
3. **Physiology** — vector H; viable ranges; autonomous drift; satiation; overshoot; critical reflexes; policy-read-only.
4. **Perception membrane** — world vs observation vs body_state; sensors/actuators stubs.
5. **Minimal embodiment** — one primary virtual habitat body with costs/affordances.
6. **Autonomous loop** — per `ORGANISM_LOOP.md`; no LLM/network/user required.
7. **Bounded arbitration** — vector urgency + commitments + embodiment filters; thrash/retry caps.
8. **Governed primitive actions** — proposal→admission→policy→contract→safety→exec→verify.
9. **Event and outcome recording** — hash-linked events; verified outcomes.
10. **Deterministic replay** — rebuild state from events to checkpoint.
11. **Restart continuity** — workers/processes do not own identity.

## Explicitly deferred (must NOT implement in D-001)

- full social relationships
- LLM communication
- advanced reflection / autobiographical Sys3
- complex personality / Big Five
- physical robotics
- reproduction
- open-ended evolution
- complete causal cognition (beyond shallow bounded models)
- production UI
- Postgres-as-primary brain
- marketplace/fleet/MCP product surfaces
- chemistry/protocell substrate

## Architecture decisions (inherited; do not re-litigate)

See `docs/evidence/d000-synthesis/conflict-decisions.json` and architecture docs. Summary:

| # | Decision | Freeze |
|---|---|---|
| 1 | Viable ranges vs setpoints | Viable ranges |
| 2 | Scalar vs vector motivation | Vector |
| 3 | Reflex vs learned regulation | Reflexes for critical; learned elsewhere |
| 4 | Event vs mutable authority | Event ledger authority + state projection |
| 5 | Memory type schemas | Working/episodic/semantic/procedural/relationship/strategic |
| 6 | Identity commitment | Signed constitutional record |
| 7 | Body migration | Same id + bind event; clone = new id |
| 8 | Capability lifecycle | Versioned grants; upgrade ≠ learning |
| 9 | Action arbitration | Soft drive competition + commitments |
| 10 | Planning bounds | Depth≤4; retry/replan caps |
| 11 | Forgetting | Bounded + consolidation |
| 12 | Relationship memory | Minimal affinity stats |
| 13 | Reflection | Bounded non-authoritative; optional |
| 14 | Online learning | Rate-limited local models |
| 15 | LLM boundary | Optional express only; not in D-001 |
| 16 | Rollback | Operator lifecycle restore/replay |
| 17 | Clone vs migration | Distinct semantics |
| 18 | Failure | Safe-torpor |

## Acceptance tests (minimum)

- Identity survives restart and model-stub replacement
- Loop runs N ticks with zero user input and zero LLM calls
- Physiology drifts and responds to verified outcomes; policy cannot assign H
- Unknown capability denied; low-risk preauth works
- Replay(events) == snapshot
- Clone creates new agent_id; migration preserves agent_id
- Memory types distinct; strategic cannot grant authority
- No production UI/robotics/LLM path required

## Non-goals / scientific humility

D-001 success does **not** authorize claims of living organism, consciousness, genuine emotion, genuine relationship, open-ended evolution, or complete companion.

## License / reuse

Clean-room only. Do not vendor AGPL AEROS, CADIA-clause AERA runtime, or unreachable PEPA code. Adapted mechanisms from D-000 independent harnesses and architecture freeze.

## Entry

Begin only after D-000S final verdict `UMBRA_D000S_FOUNDATION_ARCHITECTURE_QUALIFIED` is committed.
