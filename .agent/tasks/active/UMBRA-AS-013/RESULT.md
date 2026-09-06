# UMBRA-AS-013 — terminal result

## Verdict

`AS013_LONG_HORIZON_BOUNDEDNESS_FAIL`

## Baseline and scope

AS-013 began from `2723c50d1f06abcae60573307adfe83229def4a6` after permanent
`AS012_PROTOCOL_FAIL`. Production semantics, historical evidence, and the
qualified AS-010 full-configuration population/lifecycle were preserved.

## Result

The single fresh full-configuration boundedness organism used seed `91403101`
and completed `100000` ticks. Final snapshot, event-chain validation, Habitat
reattachment, and restart continuity passed. The unchanged frozen reduction
failed CPU fraction (`0.9955079175` versus maximum `0.05`) and database growth
(`846774272` bytes versus maximum `67108864`). RSS, RSS slope, event bound, and
the remaining continuity checks passed.

The exact CLI preflight passed before lock, including durable computed-result
checkpoint/final-result equality. The checkpoint and final boundedness result
are byte-identical. Real-time soak and causal ablation were not started under
the frozen stop rule. Production delta and retries/reseeds are `0/0`; no
successor or CLOSE-03 was started.

Evidence root:
`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-013-publication-safe-boundedness-recovery-r1/`.
