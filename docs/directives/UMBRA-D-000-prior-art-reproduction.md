# UMBRA-D-000 — Prior-Art Reproduction and Foundation Selection

**Status:** active / blocking  
**Blocks:** UMBRA-D-001 and any organism-kernel implementation  
**Product SoT:** `.agent/PROJECT_GOAL.md` (companion organism core)  
**Issued:** 2026-07-20  
**Amended:** 2026-07-20 — restore digital companion core scope; reject UMBRA-D-000A

## Governing statement

UMBRA is the persistent internal life of the companion. Avatars, robots, dialogue models, animations, and sensors are bodies and interfaces around that life. The objective is the strongest technically defensible artificial creature core for a persistent, developing, autonomous, individually recognizable companion — not molecular biology simulation.

## Rejected: UMBRA-D-000A

**Do not create or execute UMBRA-D-000A.** Artificial-life / digital-chemistry / protocell / autopoietic-membrane substrate work is rejected as a reframing of UMBRA. Chemistry and protocells are optional long-range research only and do **not** gate the companion core or D-001.

## Correction (program)

Blind greenfield coding of UMBRA-D-001 is rejected. Audit and reproduce relevant prior art before selecting foundations. Expected outcome remains a **new UMBRA companion kernel**, with informed reuse.

## Gap statement

No located project combines all of the following in one scientifically validated **companion** system:

| Capability | Required for PROJECT_GOAL |
|---|---|
| Persistent upgrade-safe identity | Individual continuity across change / body transfer |
| Endogenous homeostatic regulation | Needs drive behavior without commanded emotion |
| Autonomous behavior | Lives when unobserved |
| Embodied perception and action | Screen-boundary / body / world loop |
| Episodic / semantic / procedural memory | Developmental individuality |
| Developmental individuality | Different life histories → different individuals |
| Relationship formation | Bonding without scripted emotion commands |
| Governed physical capabilities | Safe embodiment / authority separation |
| Non-LLM organism kernel | Aliveness not from prompt performance |

## Prior-art order (mandatory)

1. MicroPsi  
2. Homeostatic reinforcement-learning systems  
3. Hexis  
4. AEROS  
5. AERA  
6. PEPA  
7. Soar / OpenCog Hyperon — only for unresolved cognitive layers  

Artificial-chemistry and protocell systems are deferred and do not gate the core companion architecture.

## Prior-art matrix (architect survey)

| Project | What matches | Critical limitation | Fit |
|---|---|---|---|
| **MicroPsi 2** | Motivation, drives, emotion as cognitive modulation, grounded representations, situated agents, simulated environments | Old Python stack; lacks modern durable identity, event provenance, robotics governance, longitudinal companion architecture | 8/10 conceptually |
| **Homeostatic Agents (PFRL)** | Internal physiological variables → state-dependent embodied behavior via homeostatic RL | Research prototype; MuJoCo stack obsolete per authors; no identity/memory/sociality/product runtime | 7/10 scientifically |
| **Hexis** | Persistent identity, autonomous heartbeat, energy budget, goals, multilayer memory, belief provenance, local operation | Fundamentally wraps an LLM; “energy” is mostly autonomy budget, not embodied physiology; no real body/world loop | 8/10 digitally |
| **AEROS** | Persistent embodied-agent identity, capability governance, hash-linked audit, memory consolidation, model/body upgrades, robot adapters | Governance/runtime shell around LLM planners — not a self-regulating organismal brain | 8/10 infrastructurally |
| **AERA** | Seed architecture, cumulative causal learning, self-generated models, real-time endogenous goals, bounded self-modification | Complex Replicode stack; weak homeostatic/companion focus; hard integration; license not clean OSD | 7/10 cognitively |
| **PEPA** | Persistent autonomy on robot dog, personality-driven endogenous goals, episodic memory, daily reflection, charging | Personality/goals substantially prompt-authored; public code incomplete vs paper claims; weak organismal causality | 7/10 behaviorally |
| **Soar / OpenCog Hyperon** | Mature cognitive architecture, memory, reasoning, planning, learning, robotics | General intelligence architectures, not artificial organisms; self-maintenance/continuity not foundational | 5/10 |
| **OpenLife** | Persistent autonomous activity, memory, async processes, budget metabolism, social emergence | Full system not open-sourced; LLM-centered; not physically embodied | High conceptual relevance; **unusable as foundation** |

## Required work (acceptance for D-000)

Execute in the order above. Each item produces artifacts under `docs/prior-art/` and a classification in `SELECTION_LEDGER.md`.

1. **MicroPsi** — reproduce/evaluate drives, motives, emotional modulators, action selection, sensor/actor separation, situated-agent loop.  
2. **Homeostatic RL** — reproduce one environment.  
3. **Hexis** — deploy/inspect persistence, heartbeat, memory; organismal vs LLM wrapper.  
4. **AEROS** — identity/governance tests without adopting organism assumptions; note AGPL blast radius.  
5. **AERA** — evaluate causal model-learning (as feasible).  
6. **PEPA** — audit public code vs paper-only claims.  
7. **Soar/Hyperon** — only if cognitive gaps remain after 1–6.  
8. Classify each: `adopt` | `adapt` | `reference` | `reject`.  
9. **Revise UMBRA-D-001** from measured results.

## Hard gates

- **Do not start UMBRA-D-001** until this directive’s acceptance criteria are met.
- **Do not create or execute UMBRA-D-000A.**
- **Do not** treat Hexis/AEROS/OpenLife-style LLM wrappers as satisfying the non-LLM organism kernel.
- **Do not** adopt AGPL into the UMBRA kernel without an explicit operator license decision.
- **Do not** claim PEPA/AERA capabilities that exist only in papers without runnable public evidence.
- Chemistry/protocell work must not delay or redefine the companion core.

## Done when

- Tracks 1–6 have written evidence (or honest BLOCKED with reason); track 7 only if needed.
- Selection ledger is complete (no TBD except explicitly deferred with owner approval).
- A revised **UMBRA-D-001** draft exists for the companion organism core.
- PROJECT_GOAL success criteria remain the evaluation bar.
