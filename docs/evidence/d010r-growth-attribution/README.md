# UMBRA-D-010R Gate-13 Growth Attribution

Non-formal diagnostic closeout for temporal-continuity performance attribution.

- Baseline: `8630ce013623fb92d7a1348cf4600109067de3d0`
- Verdict: `D010R_HISTORICAL_GROWTH_NOT_REPRODUCED_CURRENT`
- Recommendation: `CURRENT_BASELINE_D010_REQUALIFICATION_CANDIDATE`
- Evidence: `/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d010r-growth-attribution-r1/`

Historical D-010 Gate 13 remains `UMBRA_D010_PERFORMANCE_FAIL`: P0/P1/P2
failed the frozen absolute RSS-slope limit with approximately 1.90, 1.91, and
2.08 MiB/hour and approximately 39 MiB database growth. D-009 passed with
lower or flat slopes.

The historical unbounded temporal advance/observation ID-set mechanism is not
present on the current baseline. Current code bounds each set to the latest ID,
and an accelerated 2,000-tick probe measured size 1 throughout. Current
short-run probes still show an anonymous/private-dirty RSS step near the
200-tick snapshot boundary, but removing only the temporal advance payload
reproduced that step. This supports a snapshot/runtime allocator or persistence
interaction, not a confirmed production remediation target.

No production source, thresholds, historical evidence, formal run, or formal
tag changed under D-010R. A separately authorized current-baseline Gate-13
requalification is required before any qualification claim.
