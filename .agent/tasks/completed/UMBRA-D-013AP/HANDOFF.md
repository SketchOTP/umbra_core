# Handoff — UMBRA-D-013AP

```yaml
directive: UMBRA-D-013AP
status: STOPPED
verdict: D013AP_SELECTION_PATH_GAP
baseline: b0780f8fb4daaaa5ba334e008cfc2900b11b570b
phase_A:
  historical_cases: 13
  status_exhausted_exits: 5
  ap_admissible_supported_exits: 3
  unknown_semantics_zero_bias_exits: 2
  switched_to_preserving: 0
  selection_path_gap: true
integration:
  score_dimension: expected_option_preservation
  negative_only: true
  maximum_bias: -state.hysteresis
  production_files_changed: []
fresh_manifest:
  frozen_before_labels: true
  sha256: ef3e134719e089dd25770119fe1d30e385f9aa6b5abb7df88cf5cae9aef9793b
  cases: 32
formal_readiness: false
formal_p0_launched: false
formal_tag_created: false
next_phase_authorized: false
```
