# D-013P Diagnostic Reproduction

The deterministic reproduction uses the D-013O tick-270 state and the two observations preserved in docs/evidence/d013o-formal/FIRST_FAILURE.json: a distant resource and a nearby executable rest affordance.

Before correction:

    physiology:
      energy: 0.4005
      fatigue: 0.318
      integrity: 1.0
      stimulation: 0.059
    raw_needs:
      - integrity
      - stimulation
    recovery_focus_before: integrity
    fixed_order: energy, fatigue, integrity, stimulation
    selected_action: REST
    verified_rest_effect:
      energy: +0.015
      fatigue: -0.08
      integrity: +0.055
      stimulation: -0.02
    predicted_stimulation_after: 0.039
    critical_crossing_reproduced: true

The pre-fix route was reproduced by the focused D-013P test before applying the correction. The known REST effect, rather than a policy-assigned physiology credit, explains the crossing.
