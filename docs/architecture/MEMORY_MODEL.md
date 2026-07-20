# Memory Model

## Typed contracts (decision #5)

| Type | Role | Growth bound | Notes |
|---|---|---|---|
| Working | Ephemeral buffer | TTL + capacity | No automatic permanence (Track 3) |
| Episodic | Time-stamped experiences | Soft cap + consolidation | Provenance required |
| Semantic | Generalized facts | Soft cap + contradiction | Inference ≠ observation |
| Procedural | Action policies / skill stats | Cap per embodiment | Body-compatible only |
| Relationship | Partner-linked expectations | Cap per partner + global | Not full social graph in D-001 |
| Strategic (bounded) | Long-horizon notes | Hard small cap | **Cannot** override authority/physiology/identity |

## Required operations

- provenance (source, time, confidence, observation vs inference)
- contradiction detection
- correction (non-destructive)
- supersession (obsolete marked, history inspectable)
- bounded growth + consolidation/forgetting (decision #11)
- model-independent persistence (survives LLM/model swap)

## Forgetting and consolidation (decision #11)

**Accepted:** Capacity-bounded stores with periodic consolidation (merge/summarize within type) and eviction of lowest-salience non-protected items. Protected: constitutional refs, recent critical physiology events, operator-pinned.  
**Rejected:** Unlimited retention; destructive overwrite as correction.

## Relationship representation (decision #12)

D-001 minimum: `(partner_id, affinity_vector, expectancy_stats, last_events[])` derived from episodic evidence — **not** authored personality bonds. Full social cognition deferred.

## Authority

Memory never writes identity, capability grants, physiology, or verified history authority. Reflection prose is non-factual until promoted via correction protocol with provenance `inference`.
