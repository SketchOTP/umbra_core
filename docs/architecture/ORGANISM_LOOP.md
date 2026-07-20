# Organism Loop

Frozen reference loop for UMBRA companion core. Must run without user prompts, LLM, external network, or scheduled scripted personality routines.

```text
physiological drift
→ perception
→ state and memory update
→ candidate goal generation
→ goal arbitration
→ causal planning
→ governed action proposal
→ authorized execution
→ observed outcome
→ physiology update
→ causal learning
→ memory formation
→ repeat
```

## Stage contracts

| Stage | Owner | Input | Output | Authority | Failure | Persistence |
|---|---|---|---|---|---|---|
| Physiological drift | Physiology | prior H, dt | updated H | Physiology only | Clamp to critical; enter safe-torpor if past critical | H snapshot + drift event |
| Perception | Perception & Embodiment | sensors, world, body | observations (uncertain), body_state | Does not invent world truth | Mark observation unavailable; continue on last body_state | Observation events |
| State and memory update | Persistence + Memory | observations, prior state | working/episodic updates | Memory cannot rewrite constitution or verified history | Skip formation; log rejection | Transactional write |
| Candidate goal generation | Motivation | H, memory cues, commitments, external requests | candidate goals | Generates only; does not execute | Empty set → rest/explore defaults within bounds | Goal candidates ephemeral unless committed |
| Goal arbitration | Motivation | candidates + constraints | active goal set (bounded) | Selects among candidates; cannot grant capabilities | Thrash guard → hold prior commitment | Active goals in state |
| Causal planning | Causal Learning | active goals, models | plan / action proposals | Propose only | Interrupt/replan within depth/retry caps | Plan traces optional |
| Governed action proposal | Governance | proposal | admitted or denied intent | Governance admits | Deny unknown; fail-closed | Admission audit event |
| Authorized execution | Embodiment actuators via Governance | authorized intent | raw execution result | Actuators execute; cannot self-authorize | Abort; no side-effect claim | Execution event |
| Observed outcome | Perception + Governance verify | sensors + postconditions | verified outcome | Independent verify; capability may not self-certify | Mark unverified; no success learning credit | Outcome event |
| Physiology update | Physiology | verified outcome effects | new H | Physiology applies effects from outcome table | Reject policy-written H | Physiology event |
| Causal learning | Causal Learning | predicted vs observed | revised models/confidence | Models update under online-learning limits | Freeze learning on corruption | Model revision events |
| Memory formation | Memory | outcome + salience rules | episodic/procedural/… | Provenance required | Drop if over budget after consolidation attempt | Typed memory rows |

## Continuity without observers

Unprompted ticks continue while process runs. On process stop, durable state survives restart (Track 3). Absence of user input is not a stop condition (Track 6).

## Safe-torpor

If H crosses critical thresholds and no authorized recovery action is available, enter **safe-torpor**: minimize actuation, continue drift/perception at reduced rate, refuse non-recovery goals, emit torpor events. Exit when H returns to viable band or operator-authorized recovery capability runs.
