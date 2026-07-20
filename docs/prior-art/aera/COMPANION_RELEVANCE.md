# COMPANION_RELEVANCE — AERA mechanisms

## How qualified mechanisms support nonverbal companion behavior

| Companion need | Mechanism | Recommendation |
|---|---|---|
| Object affordances | Forward models `near:obj + grab → outcome` | **ADAPT** clean-room |
| Predict consequences | Forward prediction with confidence | **ADAPT** |
| Habits / routines | High-support models + inertia | **ADAPT** (with supersession) |
| Adapt after failure | Contradiction → invalidate/supersede | **ADAPT** |
| Recurring patterns | Feature-subset generalization | **ADAPT** (bounded) |
| Safe routes | Inverse + composition under cost | **ADAPT** + governance gate |
| Delayed outcomes | Explicit delay resolution before learn | **ADAPT** |
| World rule changes | Confidence drop on obsolete models | **ADAPT** |
| Act without language | Non-LLM causal store + planner | **ADAPT** |
| Survive body/model replace | SQLite/export of accepted models | **ADAPT** (Track 3/4 continuity) |

## Protections (required)

| Risk | Protection |
|---|---|
| False causal beliefs | Contradiction counters; cue features excluded from grab causal context; confidence gates |
| Runaway model generation | `MAX_MODELS` eviction of weakest |
| Repetitive failed plans | Interrupt on prediction mismatch; replan budget |
| Unsafe shortcuts | Governance: models propose, never authorize (`Authority.NONE` rejects) |
| Model duplication | Keyed observe updates same (ctx,action,outcome) |
| Obsolete habits | Supersession when rival dominates |
| Generated code execution | No exec/eval; Replicode rejected |
| Homeostasis overrides governance | Urgency only adjusts goal priority; cannot rewrite models or grant authority |

## Explicit non-adoptions

- Replicode as organism language
- AERA binary as product dependency
- Designer drives presented as endogenous autonomy
- One reasoning engine as the entire companion brain
