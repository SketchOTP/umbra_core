# ASAL-to-UMBRA offline discovery analysis

Source review: `SakanaAI/asal` at `677ba0e`. The repository identifies `substrates/`, `rollout.py`, `foundation_models/`, `asal_metrics.py`, `main_opt.py`, and `main_illuminate.py`; it describes JAX, Sep-CMA-ES for optimization, a genetic algorithm for illumination, and visual embedding metrics for open-endedness.

## Safe mapping

`UMBRA scenario` → capture structured trajectory plus renderer output → represent state with typed features and optional visual embeddings → evaluate against an offline frozen evaluator → search only declared configuration parameters → submit candidates to a quarantined review queue.

Searchable variables may include scenario seed, bounded environment parameters, schedule parameters, non-authoritative embodiment parameters, and experiment-harness parameters. Never search constitutional identity, historical evidence, verdict thresholds, authority boundaries, outcome truth, or validation labels.

Discovery data must be write-once, provenance-hashed, separated from validation storage, and forbidden from modifying qualification evidence. A candidate becomes evidence only through a fresh authorized experiment under frozen validation inputs.

Structured UMBRA state should outperform visual embeddings for energy budgets, action/outcome causality, replay divergence, relationship counters, memory retrieval precision, and authority violations. Visual embeddings may help morphology and behavioral diversity, but they are never organism authority.

Useful non-authoritative metrics include behavioral entropy, transition diversity, goal-conditioned success, causal intervention effect, recovery latency, replay exactness, and novelty under a frozen feature map. Avoid a single open-endedness score becoming a verdict.

Smallest useful prototype: an offline scorer over archived D-009-like trajectories using three or fewer bounded scenario parameters, a frozen feature extractor, a held-out seed set, and no foundation-model write path. ASAL remains discovery/hypothesis tooling only; no implementation is authorized by CC-1.
