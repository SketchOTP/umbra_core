# D-013P Root Cause

## Proven decision path

At the frozen D-013O state:

- energy: 0.4005
- fatigue: 0.318
- integrity: 1.0
- stimulation: 0.059

The unchanged diagnostic needs_recovery() reported:

    integrity, stimulation

The published D-013O trace recorded urgencies of approximately:

    energy=0.3015, fatigue=0.1200, integrity=0.0396, stimulation=0.8790

The causal contributors were:

1. ORDER = (energy, fatigue, integrity, stimulation) made integrity the first fixed-order need when no variable was already critical.
2. Sticky recovery_focus=integrity was retained because integrity remained in the recovery pool.
3. The integrity branch was direction-insensitive: it treated integrity above the viable-high bound as if it needed the same integrity-increasing REST repair used for low integrity.
4. REST was selected because the observed rest affordance was executable.
5. The verified REST template is stimulation -= 0.02; 0.059 - 0.02 = 0.039, crossing the unchanged stimulation critical-low threshold 0.05.

The arbitration path had no prospective cross-variable safety check against the architecture-owned verified outcome-effect templates before committing that recovery action.

D-013M's denial-conditioned recovery behavior was not causal to this failure and remains covered by regression tests.
