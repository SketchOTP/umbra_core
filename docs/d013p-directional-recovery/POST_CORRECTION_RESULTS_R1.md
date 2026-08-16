# D-013P-R1 Post-Correction Results

The three review cases now produce:

| case | needs_recovery | active_recovery_needs | recovery_focus | selected action |
| --- | --- | --- | --- | --- |
| high integrity only | integrity | [] | diagnostic_only | APPROACH |
| high energy only | energy | [] | diagnostic_only | APPROACH |
| low fatigue only | fatigue | [] | diagnostic_only | APPROACH |

The five legitimate directional cases remain active:

- low energy -> energy focus and CHARGE
- high fatigue -> fatigue focus and REST
- low integrity -> integrity focus and REST
- low stimulation -> stimulation focus and INSPECT
- high stimulation -> stimulation focus and REST

The original D-013O mixed state still exposes integrity diagnostically while
selecting stimulation as the actionable recovery need; unsafe REST remains
rejected by the cross-variable guard.
