# Correction rationale

The production correction is limited to umbra_core/arbitration.py.

For energy recovery APPROACH, arbitration now:

- checks the current energy focus against known APPROACH effects;
- estimates required approaches from the policy-visible distance;
- budgets known APPROACH effects and intervening autonomous drift;
- avoids committing to a demonstrably infeasible route;
- emits an existing SIGNAL_ASSISTANCE capability with explicit bounded
  unrecoverability metadata instead of entering an IDLE burn loop.

No hidden coordinates, evaluator truth, object identifiers, or post-hoc
outcomes are exposed to policy. The existing cross-variable recovery guards,
denial-conditioned recovery, directional recovery, provenance, thresholds,
effects, and V2 contract remain unchanged.
