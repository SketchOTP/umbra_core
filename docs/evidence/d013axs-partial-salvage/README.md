# D-013AXS Partial AX2 Evidence Salvage

UMBRA-D-013AXS is the completed non-formal salvage and storage-recovery
closeout for the stopped UMBRA-D-013AX2 execution.

- Verdict: `D013AXS_COMPLETED_EVIDENCE_NO_DEMONSTRATED_RESCUE`
- Parent execution: `d013ax2-20260820-r1`
- Repository baseline: `fca0b259c6c7c2e4fce6ba95d86b407b21d59994`
- Protocol fingerprint: `b3b065c2fcc06f9d1d7e4cdde59eac0b69919c9c31427f3f5456249c8c0cf07`
- External evidence root:
  `/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d013axs-partial-salvage-r1/`

## Scientific boundary

The stopped AX2 ledger records 255,022 completed branches, 468,568 pending
branches, and 33,258 in-flight branches at termination. Scientific search
depths 2 and 3 are complete; depth 4 is incomplete. No 7,200-tick
confirmation was recorded. The compact completed dataset contains zero
preliminary, viable, substantive, delay-only, or alternate-failure rescues.

This supports no demonstrated rescue in the completed evidence only. It does
not support a global negative conclusion for incomplete depth 4 or for the
unexecuted confirmation phase.

The internal depth-1 ledger phase is not a scientific forced-prefix depth;
the AX2 scientific protocol uses forced-prefix depths 2, 3, and 4.

## Preservation and reclamation

The compact dataset and hashed deterministic raw audit sample were validated
against the stopped ledger before deletion. There were 78 retained raw audit
records and no actual exception cases. Eligible result and work files were
deleted only after manifest, size, hash, and compact-equivalence checks.

The evidence root is on the governed 1-TB storage mount and is the durable
read-through location for this closeout. No production source, tests,
experiments, historical evidence, thresholds, protected agent records, formal
tag, formal P0, new AX2 branch, or confirmation was changed or created.

Architecture recommendation: `D013_CAUSAL_TARGET_RELOCALIZATION_CANDIDATE`.
Formal readiness is false. D-013AY and any AX rerun require separate
authorization.
