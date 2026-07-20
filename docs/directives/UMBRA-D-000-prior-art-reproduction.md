# UMBRA-D-000 — Prior-Art Reproduction and Foundation Selection

**Status:** active / blocking  
**Blocks:** UMBRA-D-001 and any organism-kernel implementation  
**Product SoT:** `.agent/PROJECT_GOAL.md`  
**Issued:** 2026-07-20

## Correction

Blind greenfield coding of UMBRA-D-001 is rejected. Enough relevant open-source prior art exists that UMBRA must **audit and reproduce** it before selecting foundations. Expected outcome remains a **new UMBRA kernel**, built with informed reuse — not reinventing decades of cognitive-architecture research, and not adopting any single project as “the organism.”

## Gap statement (why UMBRA still exists)

No located project combines all of the following in one scientifically validated system:

| Capability | Required for PROJECT_GOAL |
|---|---|
| Persistent upgrade-safe identity | Individual continuity across change |
| Endogenous homeostatic regulation | Causal self-maintenance / energy-matter flows |
| Autonomous behavior | Lives when unobserved |
| Embodied perception and action | Screen-boundary / body / world loop |
| Episodic / semantic / procedural memory | Developmental individuality |
| Developmental individuality | Different life histories → different individuals |
| Relationship formation | Bonding without scripted emotion commands |
| Governed physical capabilities | Safe embodiment / authority separation |
| Non-LLM organism kernel | Aliveness not from prompt performance |

UMBRA occupies that gap. Prior art covers **major pieces**; none is a drop-in organism.

## Prior-art matrix (architect survey)

| Project | What matches | Critical limitation | Fit |
|---|---|---|---|
| **MicroPsi 2** | Motivation, drives, emotion as cognitive modulation, grounded representations, situated agents, simulated environments | Old Python stack; lacks modern durable identity, event provenance, robotics governance, longitudinal companion architecture | 8/10 conceptually |
| **Hexis** | Persistent identity, autonomous heartbeat, energy budget, goals, multilayer memory, belief provenance, local operation | Fundamentally wraps an LLM; “energy” is mostly autonomy budget, not embodied physiology; no real body/world loop | 8/10 digitally |
| **AEROS** | Persistent embodied-agent identity, capability governance, hash-linked audit, memory consolidation, model/body upgrades, robot adapters | Governance/runtime shell around LLM planners — not a self-regulating organismal brain | 8/10 infrastructurally |
| **PEPA** | Persistent autonomy on robot dog, personality-driven endogenous goals, episodic memory, daily reflection, charging | Personality/goals substantially prompt-authored; public code incomplete vs paper claims; weak organismal causality | 7/10 behaviorally |
| **AERA** | Seed architecture, cumulative causal learning, self-generated models, real-time endogenous goals, bounded self-modification | Complex Replicode stack; weak homeostatic/companion focus; hard integration; license not clean OSD | 7/10 cognitively |
| **Homeostatic Agents (PFRL)** | Internal physiological variables → state-dependent embodied behavior via homeostatic RL | Research prototype; MuJoCo stack obsolete per authors; no identity/memory/sociality/product runtime | 7/10 scientifically |
| **Soar / OpenCog Hyperon** | Mature cognitive architecture, memory, reasoning, planning, learning, robotics | General intelligence architectures, not artificial organisms; self-maintenance/continuity not foundational | 5/10 |
| **OpenLife** | Persistent autonomous activity, memory, async processes, budget metabolism, social emergence | Full system not open-sourced; LLM-centered; not physically embodied | High conceptual relevance; **unusable as foundation** |

### Notes on the closest ancestors

1. **MicroPsi 2** — Strongest intellectual ancestor (motivation, grounded cognition, drives, action regulation, situated agents). MIT. Treat as theoretical + implementation **reference**, not production foundation (documented Python 3.4/3.5-era stack).
2. **Hexis** — Closest modern digital companion substrate (Postgres cognitive state, identity, multilayer memory, heartbeat, goals, evidence history). MIT. Structural flaw: LLM remains the conscious action loop; DB supplies continuity around it — convincing character ≠ organism from embodied regulation.
3. **AEROS** — Closest identity/governance layer (immutable identity, capability modules, policy gates, audit chains, consolidation, ROS adapters). Core AGPL-3.0 (commercial constraint); schemas/SDK often Apache-2.0. Reusable research/possibly code — **governs** intelligence; does not supply organismal motivation.
4. **PEPA** — Closest demonstrated robotic behavior (Unitree, goals, episodic memory, charge-seeking). Distinguish public navigation-focused code from paper-only cognitive claims; individuality largely linguistically imposed.
5. **AERA** — Strongest constructivist-learning candidate. Specialized, incomplete in places; modified BSD with use restrictions — source-available, not clean OSS adopt.
6. **Homeostatic RL (Yoshida et al. PFRL)** — Direct evidence physiology → behavior. Excellent experimental baseline; poor software foundation.
7. **OpenLife** — Conceptually close; intentionally not a usable OSS foundation.

## Required work (acceptance for D-000)

Execute in a governed, evidence-backed order. Each item produces artifacts under `docs/prior-art/` and a classification row in the selection ledger.

1. **Reproduce MicroPsi’s motivational loop** (minimal runnable slice: drives → modulators → action tendency in its sim or a stripped harness).
2. **Deploy and inspect Hexis** persistence, heartbeat, and memory layers; document what is organismal vs LLM wrapper.
3. **Run AEROS identity/governance tests** without adopting its organism assumptions; note AGPL blast radius.
4. **Reproduce one homeostatic-RL environment** from the PFRL/homeostatic agents line (or documented successor if MuJoCo path is dead).
5. **Evaluate AERA’s causal model-learning mechanism** (read/run what is feasible; do not force full integration).
6. **Audit PEPA’s available code** — public implementation vs paper-only claims.
7. **Classify each component:** `adopt` | `adapt` | `reference` | `reject` (with license + technical rationale).
8. **Revise UMBRA-D-001** from measured results (informed kernel plan, not blind greenfield).

### Selection ledger (fill during work)

| Component | Classification | License | Evidence path | Notes |
|---|---|---|---|---|
| MicroPsi 2 motivational loop | TBD | MIT | | |
| Hexis persistence/heartbeat/memory | TBD | MIT | | |
| AEROS identity/governance | TBD | AGPL-3.0 / Apache-2.0 | | |
| Homeostatic RL env | TBD | (verify) | | |
| AERA causal learning | TBD | modified BSD | | |
| PEPA public code | TBD | (verify) | | |
| OpenLife | reject (foundation) | N/A (not released) | | Conceptual only |
| Soar / Hyperon | TBD | | | Likely reference at most |

## Hard gates

- **Do not start UMBRA-D-001** until this directive’s acceptance criteria are met and recorded in `.agent/OUTCOMES.md`.
- **Do not** treat Hexis/AEROS/OpenLife-style LLM wrappers as satisfying PROJECT_GOAL’s non-LLM organism kernel.
- **Do not** adopt AGPL into the UMBRA kernel without an explicit operator license decision.
- **Do not** claim PEPA/AERA capabilities that exist only in papers without runnable public evidence.
- Reuse is encouraged; **cargo-culting an entire foreign architecture as “the creature” is forbidden.**

## Done when

- All six reproduction/audit tracks have written evidence (or honest BLOCKED with reason).
- Selection ledger is complete (no TBD except explicitly deferred with owner approval).
- A revised **UMBRA-D-001** draft exists, citing which prior-art pieces are adopt/adapt/reference/reject.
- PROJECT_GOAL success criteria remain the evaluation bar; prior art does not weaken them.
