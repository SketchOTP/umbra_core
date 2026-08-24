# UMBRA-D-014H2 production trace and H1 translation

Terminal verdict: `D014H2_UNIFIED_POOL_BASELINE_FAIL`.

Permanent retained evidence is finalized at:
`\atlas\ATLAS\100_ACTIVE\Projects\UMBRA-CORE\evidence\live-evidence\d014h2-production-trace-translation-r1/`

The opt-in, default-disabled production trace passed parity/replay and real-row translation through unchanged H1. Downstream viability did not qualify: fixed R0 completed 8/8 x7200, known R1 reproduced the tick-372 fatigue failure, R1 holdouts failed, and the first R2 holdout stopped at an existing runner HabitatWriteRejected at its scheduled occlusion. No retry or remediation occurred.

Active SQLite/WAL/AF_UNIX scratch is local/direct-attached only and is not authoritative evidence. D-014I, formal D-014, D-013/AX, and remediation are not authorized automatically.
