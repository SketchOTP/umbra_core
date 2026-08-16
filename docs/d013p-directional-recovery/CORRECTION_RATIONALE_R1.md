# D-013P-R1 Correction Rationale

The arbitration path now uses only active_recovery_needs() for autonomous
recovery targeting. needs_recovery() remains the complete diagnostic band
report and is not promoted back into the recovery pool.

When a diagnostic-only overshoot exists, the arbitration state records the
explicit non-target marker diagnostic_only so existing cross-component urgency
awareness remains intact. Candidate effects that push a diagnostic-only
variable farther outside its viable band are excluded using the existing
architecture-owned OUTCOME_EFFECTS table. No physiology threshold or outcome
effect changed.

This preserves the D-008 memory behavior without selecting integrity repair,
energy recovery, or fatigue reduction for a diagnostic-only condition.
