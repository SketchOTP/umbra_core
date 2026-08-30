# UMBRA-CLOSE-02Z handoff

directive: UMBRA-CLOSE-02Z
status: TERMINAL
verdict: CLOSE02Z_CANDIDATE_STABLE_STOCHASTIC_COMPOSITION_QUALIFIED

baseline:
  start: 8300c637fb4af859c48632020246320db308d024
  governance_start: 73991e2b970856df438333507e2e381b1aace710
  restoration: 3901c9a486216bee4c02f644e35b6f3b2d9e91aa
  implementation: aee1e42c010bd3ef174e0db6efa666ea8674f577
  freeze: f828813c4af37cc1862d94cabaa8ef2e3d197dc2
  closeout: 0df181e0f6de184cdd1907169f553817c830041a

contract:
  schema: CANDIDATE_STABLE_STOCHASTIC_TERM_V1
  namespace: ordinary_candidate_competition:v1
  organism_basis: persisted SeededRNG.seed
  tick: authoritative active tick
  candidate_identity: canonical source-neutral behavioral identity
  sigma: 0.08
  shared_candidate_rng_cursor: false

compatibility:
  diagnostic_A: 500/500 PASS
  diagnostic_B: 3500/3500 PASS
  known_R1_run: false
  viability_population_runs: 0

validation:
  focused: PASS
  distribution: PASS
  tick_569_replay: PASS
  applicable_suite: 957 pass / 12 baseline-reproduced fail / 2 skip
  new_regressions: 0
  authority3: PASS
  governance: PASS
  evidence_manifest: PASS
  notion_refetch: PASS

integrity:
  retries: 0
  reseeds: 0
  fatigue_support_changed: false
  positive_preparation_changed: false
  historical_evidence_modified: false

evidence:
  root: /srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02z-candidate-stochastic-r1/
  manifest_sha256: df02f07ab471bfab5cb6e13a8373b333a2c76f571511ee1bba54b785415e8687

recommendation: UMBRA-CLOSE-02AA_PROSPECTIVE_SUPPORT_ACQUISITION_AND_POSITIVE_PREPARATION_REPLAN
next_phase_authorized: false
