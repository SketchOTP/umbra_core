# UMBRA Reference Architecture

**Status:** Frozen by UMBRA-D-000S  
**Evidence base:** D-000 Tracks 1–6 (committed)  
**Verdict gate:** `UMBRA_D000S_FOUNDATION_ARCHITECTURE_QUALIFIED`  
**Implementation directive:** `docs/directives/UMBRA-D-001-invariant-companion-core.md`

## Purpose

Define the smallest evidence-backed companion organism core for UMBRA. Bodies, UIs, LLMs, and robotics are interfaces around this core. No production kernel is authorized by this document alone.

## Module map

| Module | Authority | Primary evidence |
|---|---|---|
| Constitutional Identity | Owns agent_id, lineage, birth, lifecycle, operator root, embodiment history | Track 4 AEROS |
| Physiology | Owns vector regulatory state H; drift; satiation; critical reflexes | Tracks 1–2 |
| Perception & Embodiment | World truth vs observation; sensors/actuators; one primary body | Tracks 1, 4, 6 |
| Memory | Typed stores with provenance; model-independent | Track 3 Hexis |
| Causal Learning | Forward/inverse models; revision; bounded planning | Track 5 AERA |
| Motivation & Goal Arbitration | Vector urgency + history + commitments; no scalar happiness | Tracks 2, 6 |
| Capability Governance | Proposal → admit → policy → contract → safety → exec → verify | Track 4 |
| Persistence | SQLite WAL event/state authority; optional indexes/Postgres scale | Track 3 |
| Reflection & Language | Bounded, optional, non-authoritative | Track 6 (adapt structure; reject LLM will) |

## Organism loop (frozen)

See `ORGANISM_LOOP.md`. Loop continues without user prompts, LLM, network, or scripted routines.

## Non-negotiable separations

1. **Learned systems propose; they never authorize** (Tracks 4–5).
2. **Policies may read physiology; they may not write it** (Track 2).
3. **Identity excludes personality, memories, model, body, skills, mood, preferences** (Track 4).
4. **LLM may express; never own identity, physiology, motivation, authority, memory truth, or existence** (Tracks 3–6; PROJECT_GOAL).
5. **Lived history alters behavior; authored traits do not constitute individuality** (Tracks 3, 6).

## Stack freeze (D-001)

- Platform: Linux
- Persistence: SQLite WAL primary (`HYBRID_PRIMARY`)
- Core loop: deterministic, non-LLM
- Clean-room reimplementation of adapted mechanisms (no AGPL/CADIA product deps)

## Related docs

- `ORGANISM_LOOP.md` — stage ownership
- `MODULE_AUTHORITY_MATRIX.md` — write/read rights
- `STATE_AND_EVENT_MODEL.md` — ledger vs state
- `IDENTITY_AND_LIFECYCLE.md` — continuity semantics
- `MEMORY_MODEL.md` — typed memory
- `LEARNING_AND_PLANNING.md` — causal bounds
- `GOVERNANCE_AND_CAPABILITIES.md` — action chain
- `LLM_BOUNDARY.md` — language limits
- `OPEN_QUESTIONS.md` — non-blocking unknowns

## Scientific claim authorized

A modular companion core with constitutional identity, vector homeostasis, typed provenance memory, governed action, bounded causal models, and history-dependent arbitration can be specified without an LLM controller or authored personality — based on D-000 independent mechanism qualifications.

## Claims not authorized

Living organism; consciousness; genuine emotion; genuine relationship; open-ended evolution; complete companion product.
