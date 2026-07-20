# COMPANION_RELEVANCE

## Believable companion support

| Capability | Homeostatic mechanism contribution |
|---|---|
| Spontaneous rest | Low drive + action cost → STAY / idle |
| Waking / activity cycles | Drift raises drive → endogenous action |
| Need-dependent exploration | Novelty only when deficits small (C8 pattern) |
| Selective engagement | Competition among needs; not always-on attention |
| Satiation from interaction | Same as resource satiation — must apply to social channels later |
| Behavior during user absence | Autonomous drift (I9) — **required** |
| Preparation for predictable events | Anticipatory forward model / learned delays |
| Recovery after disruption | Drive-reduction seeking after I1–I4 style shocks |
| Non-manipulative bids for assistance | Only if help is a regulated affordance with satiation — **not** reward-max attention |

## Architectural answers (Track 2)

1. **Point vs viable range:** Prefer **viable ranges**; ideals optional for physiology.
2. **Shared drive function:** Shared family OK; per-need weights allowed; do not force one psych setpoint function onto all needs.
3. **Scalar vs vector-preserving:** Keep **vector \(H\)**; scalarize only for a learning signal, not as the creature’s whole state.
4. **Optimize drive reduction directly?** As a **learning signal**, yes (ADAPT). As the entire brain, no.
5. **Non-learned reflex?** Yes — critical-bound reflexes / safety clamps remain non-learned.
6. **Anticipation representation:** Separate predictor / forward model over \(H\) and env delays; not hard-coded schedules alone.
7. **Action costs × low energy:** Movement should cost energy; prevents thrashing; calibrated carefully.
8. **Satiation vs endless engagement:** Drive reduction + overshoot + explicit interaction satiety variables.
9. **Learned physiology?** Authority of \(H\) stays **deterministic**; learning may refine predictors, not rewrite ground-truth physiology unchecked.
10. **Policy receives:** Interoception + exteroception; never write-access to \(H\).
11. **Expression receives:** Read-only projections of \(H\) / modulators — expression ≠ will.
12. **Continuous lifelong RL training?** **No** as default; bounded / offline / gated updates only.
13. **Identity under policy upgrades:** Versioned policies; physiology + memory continuity; no silent full retrain.
14. **Interpretable for audit:** Vector \(H\), drive components, reward terms, separation boundary.
15. **Anti-flattening:** Multiple authorities (phys, memory, relation, development); forbid single happiness scalar; forbid RL-as-brain.

## Smallest defensible regulatory substrate (Track 2 claim)

```text
vector H with viable ranges
+ autonomous drift
+ authenticated outcome updates
+ drive-reduction learning signal (optional policy)
+ hard physiology/policy separation
+ satiation / overshoot
+ anticipatory prediction (bounded)
```

Does **not** include: LLM controller, scripted emotion commands, production MuJoCo stack, unlimited online RL.
