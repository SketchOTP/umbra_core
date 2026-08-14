# Metric Pair Contract

Metric: `habitat_continuity_l2`, source `_run_integrated_trace`, owner one
subject row, units bounded continuity distance. Per-subject values are
transformed to `1 - value`, paired by seed, and passed to the frozen comparison
direction. Missing, duplicate, orphan, stale, mixed-role, mixed-execution, or
third-subject rows fail closed; no row can enter both arms.
