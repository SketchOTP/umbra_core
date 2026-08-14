# ASAL-to-UMBRA offline discovery analysis

Source review: `SakanaAI/asal` at `677ba0e`. The repository identifies `substrates/`, `rollout.py`, `foundation_models/`, `asal_metrics.py`, `main_opt.py`, and `main_illuminate.py`; it describes JAX, Sep-CMA-ES for optimization, a genetic algorithm for illumination, and visual embedding metrics for open-endedness.

## Safe mapping

`UMBRA scenario` → capture structured trajectory plus renderer output → represent state with typed features and optional visual embeddings → evaluate against an offline frozen evaluator → search only declared configuration parameters → submit candidates to a quarantined review queue.

Searchable variables may include scenario seed, bounded environment parameters, schedule parameters, non-authoritative embodiment parameters, and experiment-harness parameters. Never search constitutional identity, historical evidence, verdict thresholds, authority boundaries, outcome truth, or validation labels.

Discovery data must be write-once, provenance-hashed, separated from validation storage, and forbidden from modifying qualification evidence. A candidate becomes evidence only through a fresh authorized experiment under frozen validation inputs.

Structured UMBRA state should outperform visual embeddings for energy budgets, action/outcome causality, replay divergence, relationship counters, memory retrieval precision, and authority violations. Visual embeddings may help morphology and behavioral diversity, but they are never organism authority.

Useful non-authoritative metrics include behavioral entropy, transition diversity, goal-conditioned success, causal intervention effect, recovery latency, replay exactness, and novelty under a frozen feature map. Avoid a single open-endedness score becoming a verdict.

## Engineering recommendation

```yaml
asal_for_umbra:
  recommended: true
  recommended_scope: offline discovery and failure-region search only
  prohibited_scope: organism control, identity semantics, qualification, verdicts, evidence interpretation
  prototype_goal: rank bounded scenario and embodiment configurations against frozen offline trajectories
  inputs: typed trajectories, renderer frames as optional secondary features, seed manifest, bounded parameters
  outputs: candidate configurations, feature scores, provenance hashes, held-out reports
  search_variables: [scenario generation, arbitration operating regions, homeostatic robustness, behavioral diversity, development opportunities, habitat challenge configurations, expression diversity, failure-region discovery]
  protected_variables: [qualification thresholds, formal evidence interpretation, constitutional identity semantics, governance safety rules, historical verdicts]
  discovery_metrics: [behavioral entropy, transition diversity, causal intervention effect, recovery latency, replay exactness, held-out success]
  scientific_contamination_controls: [write-once discovery store, frozen evaluator, held-out seeds, provenance hashes, no validation writes]
  dependencies: [JAX, optional GPU, optional CLIP/DINO; no production dependency]
  estimated_complexity: small research prototype
  expected_value: medium-to-high for hypothesis generation; zero authority value
```

Smallest useful prototype: an offline scorer over archived D-009-like trajectories using three or fewer bounded scenario parameters, a frozen feature extractor, a held-out seed set, and no foundation-model write path. ASAL remains discovery/hypothesis tooling only; no implementation is authorized by CC-1.
