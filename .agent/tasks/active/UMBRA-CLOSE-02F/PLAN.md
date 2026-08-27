# UMBRA-CLOSE-02F

Status: ACTIVE

Baseline: `c4f387433f42ffa5517b40c0667a97b6e03af4d0`

This packet tracks the file-scoped durability qualification and the gated
qualification program. CLOSE-02 and CLOSE-02Q remain terminal and are not
being retried. Production source, historical evidence, and protected dirty
state are preserved.

Immediate gate: inspect `/srv/ATLAS` semantics, then run two sequential
file-scoped durability probes at the new CLOSE-02F evidence root. Do not use
`sync`, `sync -f`, or `syncfs`.
