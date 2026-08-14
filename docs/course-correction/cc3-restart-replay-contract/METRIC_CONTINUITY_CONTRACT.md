# Metric Continuity Contract

`ticks`, `max_objects`, `max_zones`, and `boundedness_ok` are
`AGGREGATED_ACROSS_SEGMENTS`. `habitat_continuity_l2` is
`CONTINUOUS_ACROSS_SEGMENTS` and follows the existing D-009 convention,
including state-version distance when hashes match. `verified_outcomes` is
`CONTINUOUS_ACROSS_SEGMENTS`. No restart boundary is counted as an extra
observation. Negative checks reject duplicate aggregation, segment mixing,
wrong denominators, missing pre-segment data, and missing post-segment data.
