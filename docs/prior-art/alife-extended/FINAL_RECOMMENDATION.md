# Final recommendation

## Direct answers

- UMBRA-CORE redundant: **No.** Its primitives are established, but the audited systems do not provide the same persistent single-individual authority synthesis.
- Abandon UMBRA-CORE: **No.**
- Architecture change required: **No production architecture change is authorized or required by CC-1.**
- First action after CC-1: **build one read-only harness contract test around the existing qualified scenario boundary**, because harness invalidation is the highest demonstrated operational risk and this yields evidence before any substrate choice.
- Do not yet: add dependencies, replace identity/memory/authority modules, run external integration experiments, or begin CC-2.

```yaml
directive: UMBRA-D-000X
verdict:
  umbra_redundant: false
  abandon_umbra: false
  architecture_change_required: false
  production_code_change_authorized: false
prior_art:
  projects_reviewed: 14
  projects_code_reviewed: 7 pinned repositories/source trees
  mechanisms_compared: 39 required dimensions plus reuse and authority dimensions
umbra:
  established_prior_art: [autonomous organisms, embodiment, energy behavior, adaptation, memory-like mechanisms, evolution, self-organization]
  defensible_distinctive_contributions: [constitutional identity independent of body, body transfer continuity, verified-outcome autobiographical authority, partner-specific continuity, governed capability authority, authoritative birth replay]
  unsupported_novelty_claims: [first non-LLM ALife, first embodied organism, first homeostatic organism, first memory-bearing organism]
  justified_custom_implementations: [identity authority, governed evidence, body-independent continuity, verified outcome semantics]
  unjustified_duplications: []
reuse:
  adopt_directly: []
  adapt_cleanly: [MABE2 modular harness concepts, ASAL offline evaluator concepts]
  reference_only: [Avida, Lenia, Evochora, Ribossome, Tierra, Aevol, Evo2Sim]
  external_benchmarks: [ALIEN, Polyworld]
  external_research_substrates: [DISHTINY, MABE2 population runtime]
  rejected: [foundation-model authority, body-is-genome identity, chemistry replacement]
  license_blocked: [Ribossome, Aevol/Tierra direct-use terms]
  needs_further_test: [ALIEN/Polyworld adapter gates, ASAL contamination controls, non-identity Ribossome mechanisms]
recommended_cc2:
  architecture_changes: [none authorized by CC-1; consider internal harness contracts]
  modules_affected: [future experiment infrastructure only]
  modules_unchanged: [identity, authority, sealed evidence, qualification thresholds]
  first_external_integration_candidate: quarantined custom deterministic embodiment benchmark
  first_experiment_infrastructure_change: modular harness contract tests
  discovery_prototype_recommended: ASAL-inspired offline structured-state search
scientific_integrity:
  prior_verdicts_modified: false
  sealed_evidence_modified: false
  formal_thresholds_modified: false
repo_state:
  branch: master
  d000x_closeout_head: 5979ac03df7cd4ec74d93a79b0685998aca9e94d
  clean: false
blockers:
  - pre-existing operator file .agent/LIBRARY_REVIEW.md remains unmodified and uncommitted
  - Aevol, Tierra, Stringmol, and Evo2Sim remain UNKNOWN_AFTER_REVIEW at source-detail level
  - Mimir V2 tools unavailable
```

CC-1 is complete as a research closeout. CC-2 remains unauthorized and blocked pending operator review.

```yaml
directive: UMBRA-D-000X
status: COMPLETE
verdict:
  umbra_redundant: false
  abandon_umbra: false
  architecture_change_required: false
  cc2_recommended: true
  cc2_authorized: false
research:
  projects_platform_reviewed: 14
  projects_source_reviewed: 7
  mechanisms_compared: 39 plus authority, persistence, harness, licensing, and embodiment dimensions
  unresolved_source_questions: [Aevol pin/license details, Tierra canonical source, Stringmol/Evo2Sim source-level detail]
novelty:
  established_prior_art: [autonomous organisms, energy behavior, embodiment, sensorimotor loops, adaptation, memory-like mechanisms, evolution, self-organization]
  defensible_umbra_distinctions: [persistent constitutional identity independent of body, single-individual lived-history continuity, verified-outcome learning authority, partner-specific continuity, governed capability authority, authoritative replay]
  unsupported_claims_withdrawn: [first non-LLM ALife, first embodied organism, first homeostatic organism, first memory-bearing organism]
duplication:
  justified: [identity authority, governed evidence, body-independent continuity, verified outcomes, deterministic companion replay]
  unjustified: []
  partial: [experiment harness modularity]
reuse:
  adopt_directly: []
  adapt_cleanly: [MABE2 harness boundaries, ASAL offline evaluator pattern]
  architecture_patterns: [MABE2 modular responsibilities, Evochora persistence/indexing separation]
  research_tools: [ASAL-inspired structured-state offline search]
  external_benchmarks: [custom deterministic benchmark tier, conditional ALIEN/Polyworld tier]
  reference_only: [Avida, Lenia, CAX, Evochora, Ribossome, Aevol, Stringmol, Evo2Sim, Tierra]
  rejected: [foundation-model authority, body-is-genome identity, chemistry replacement, population continuity as companion identity]
  license_blocked: [Ribossome, unresolved Aevol/Tierra direct-use terms]
  needs_further_test: [external adapter gates, ASAL contamination controls]
next_course:
  single_highest_priority_action: build one read-only harness contract test around the existing qualified scenario boundary
  why: historical harness failures are the highest demonstrated operational risk
  expected_benefit: catches wrong-path, condition, aggregation, metric, budget, freeze, and contamination defects before qualification
  affected_modules: future experiment infrastructure only
  production_change_required: false
review:
  independent_review: APPROVE_WITHOUT_CRITICAL_OR_IMPORTANT_FINDINGS
  unresolved_findings: [documented UNKNOWN_AFTER_REVIEW source questions]
scientific_integrity:
  production_code_modified: false
  sealed_evidence_modified: false
  historical_verdicts_modified: false
  historical_thresholds_modified: false
commits:
  governance: 42ce903
  dossier: 437db68
  corrections: 367fa6b
  review: 367fa6b
  d000x_closeout_commit: 5979ac03df7cd4ec74d93a79b0685998aca9e94d
  baseline_commit: e0d9ee8ac91381f10cc9e125568ddd4dd9c3a6b2
repo:
  d000x_closeout_head: 5979ac03df7cd4ec74d93a79b0685998aca9e94d
  branch: master
  clean: false
blockers: []
```
