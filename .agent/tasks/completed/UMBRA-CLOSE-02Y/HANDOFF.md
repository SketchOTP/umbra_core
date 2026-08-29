# UMBRA-CLOSE-02Y handoff

directive: UMBRA-CLOSE-02Y
status: TERMINAL
verdict: CLOSE02Y_CANDIDATE_STABLE_STOCHASTIC_CONTRACT_SUPPORTED

baseline:
  start_commit: 80bcec23e02ec465307b72e9256e38d00305e81b
  governance_start: dd0098247fdd02cd9c76d491d69f7baa00e1289d
  closeout_commit: recorded by publication closeout
  remote_master: recorded by publication closeout

contract:
  organism_basis: persistent existing basis
  tick: authoritative active tick
  namespace: versioned candidate-scoring namespace
  candidate_identity: canonical source-neutral behavioral identity
  candidate_index_used: false
  candidate_count_used: false
  proposal_order_used: false
  proposal_source_used: false

validation:
  stochastic_path_audit: PASS
  identity_audit: PASS
  prior_art_translation: PASS
  pure_contract_tests: 10/10 PASS
  retained_tick_569_replay: PASS
  permutation_insertion_deletion: PASS
  restart_and_migration: PASS
  individuality_conflict: false
  authority3: PASS
  governance: PASS
  evidence_manifest: PASS

integrity:
  production_changes: 0
  organism_runs: 0
  retries: 0
  reseeds: 0
  rollback: false
  fatigue_support_changed: false
  positive_preparation_changed: false

evidence:
  root: /srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02y-stochastic-composition-r1/
  manifest_sha256: 5979f1a1ebb6f3cddedf4fa1617826775f54f87871b0cebd881f9abe15754747

recommendation: UMBRA-CLOSE-02Z_CANDIDATE_STABLE_STOCHASTIC_IMPLEMENTATION_CANDIDATE
next_phase_authorized: false
