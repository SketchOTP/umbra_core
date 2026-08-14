# Perception error analysis

The formal estimate was `1.340481645595797`, while authoritative distance was
`1.5167094947389301`. The estimate is inside the arbitration `<= 1.5` charge
cutoff; the authoritative value is outside it. Confidence was high but not
certainty (`0.8974`, uncertainty `0.1026`).

This is a bounded perception error, not world-truth leakage or corruption.
The membrane's Gaussian estimate/noise model makes this divergence an expected
part of the architecture. The correct downstream behavior is safe denial plus
learning, which is what occurred.
