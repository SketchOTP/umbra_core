# AS-008 result

Status: terminal; AS-008 formal execution stopped at the first post-lock
protocol failure.

AS-007 is preserved as terminal `AS007_PROTOCOL_FAIL`. Its valid inherited diagnostics are not being rerun. AS-008 production semantics must remain exactly the AS-007 frozen implementation.

Pre-formal gates passed: implementation inheritance, seed disjointness,
downstream preflight, and protected tests `50/50` twice. Formal execution is
governed by the frozen AS-008 population lock in the evidence root.

Terminal verdict: `AS008_PROTOCOL_FAIL`. The one frozen command completed R0
`8/8` and R1 `8/8` at 7,200 ticks each (`16` completed rows, `115200`
completed ticks), then failed at the first R2 case because
the inherited D-014 scenario attempted direct partner occlusion mutation while
the HabitatEngine sole-writer guard was attached. The first R2 organism was
created and advanced `2399` ticks before that pre-tick-2400 exception; it did
not produce a completed summary row. Thus `17` organisms were created and
`117599` ticks executed in total. Completed formal evidence is retained; R2/R3,
lifecycle, boundedness, soak, and ablation were not run. The clarification is
append-only in `AS008_PROTOCOL_FAILURE_CORRECTION.json`; the original terminal
artifact is unchanged.
