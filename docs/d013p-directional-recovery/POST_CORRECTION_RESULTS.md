# D-013P Post-Correction Results

Using the same deterministic D-013O boundary:

    active_recovery_needs:
      - stimulation
    recovery_focus_before: integrity
    recovery_focus_after: stimulation
    selected_action: MOVE
    predicted_stimulation_after: 0.062
    predicted_critical_crossing: false
    stimulation_protected: true

The selected action came from normal arbitration. It was not scripted as a required replacement capability. The exact-state focused tests also directly verify that REST's known effect is rejected when it would create a new critical boundary in another variable.
