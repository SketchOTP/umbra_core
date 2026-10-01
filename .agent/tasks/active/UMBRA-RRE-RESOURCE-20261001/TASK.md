# Task start — 2026-10-01

User authorizes narrow production enforcement of the existing 32 movement-step
recovery-route bound, followed by bounded resource characterization.
Baseline: f132c003f41fca92aa6dcd63e1b43abb9d55c2b6.
Branch: rre-bound-resource-20261001. No formal launch or master merge.

Reject complete over-limit routes as UNKNOWN_ROUTE before route projection;
never truncate, raise the cap, or reinterpret uncertainty as impossibility.
The proposed ordinary action retains existing immediate safety assessment;
count every movement execution in the complete recovery continuation from its
projected state, not just a truncated prefix.

Measurement: canonical AS-018 full configuration, P2 R0/S0, one prospectively
registered excluded-development seed. Cadence 100 ticks or 5 seconds (first),
plus both sides of compaction/restart/export. Record database/WAL/SHM separately,
retained checkpoints/provenance/snapshots, exported evidence and RSS.
Require five natural compactions including oldest-generation eviction and
same-identity restart/export. Hard stop 30000 total ticks; no extension/retry.
Insufficient coverage remains insufficient. Storage limits are proposed only
after measurements, scoped to this profile and measured execution host.

Preserve accepted auditor, historical runner-reported PASS with detailed
evidence unavailable, consumed/retired seeds, negatives and operator RECORD.md.
Changed production receives no inherited formal qualification credit.
