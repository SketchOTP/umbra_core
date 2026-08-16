# D-013P Correction Rationale

The smallest existing mechanism was used: recovery arbitration.

Physiology.active_recovery_needs() separates the complete diagnostic band report from directionally actionable recovery:

- energy and integrity are actionable when below their viable-low bounds;
- fatigue is actionable when above its viable-high bound;
- stimulation remains actionable on either side of its viable band.

The arbitration path uses active needs when present, while retaining the historical diagnostic fallback when no directional need exists so unrelated established behavior is not silently rewritten.

Arbitrator._introduces_critical_boundary() projects only the known, architecture-owned verified outcome-effect template. commit_safe_recovery() rejects an action only when it would make another currently non-critical variable critical, then selects a safe architecture-generated alternative. The recovery target itself is not treated as a cross-variable hazard; this preserves D-013A's energy-focus approach behavior.

No special tick, seed, numeric state, evaluator exemption, rescue path, threshold relaxation, or REST-effect change was added.
