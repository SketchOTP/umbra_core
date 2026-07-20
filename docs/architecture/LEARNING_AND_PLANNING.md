# Learning and Planning

## Causal learning owns

- forward models (predict effects)
- inverse models (propose actions toward goals)
- prediction confidence from evidence
- contradiction-driven revision
- affordance learning (embodiment-scoped)
- bounded model composition
- interruptible planning

Evidence: Track 5 independent reproduction.

## Authority

Learned models **propose** actions. They **may not** authorize effects (Track 5 REJECT `learned_models_grant_authority`).

## Planning bounds (decision #10)

| Bound | Default freeze | Rationale |
|---|---|---|
| Max plan depth | 4 | Track 5 MAX_PLAN_DEPTH; C2≫C5 |
| Max active models composed | small fixed N | Prevent combinatorial explosion |
| Max replans per tick | fixed | Interruptible planning |
| Max retries per goal | fixed (Track 6 MAX_RETRIES) | Anti thrashing |

## Online-learning limits (decision #14)

**Accepted:** Bounded online updates (confidence-weighted tabular/local models; rate-limited revision).  
**Rejected:** Unlimited continuous retraining of a monolithic policy as the creature brain (Track 2 REJECT).

Batch/offline refinement allowed later under governance; never unconstrained identity-drifting retrain.

## Arbitration method (decision #9)

See Motivation section in reference architecture: soft competition over vector drives + commitments + embodiment filters; not fixed priority lists; not one scalar reward (Tracks 2, 6).

## Reflex vs learned (decision #3)

Critical safety reflexes are non-learned physiology/governance paths. Learned regulation may modulate non-critical behavior only.
