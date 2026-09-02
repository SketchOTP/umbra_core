# Evidence

Canonical evidence root:

`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r5-common-root-modal-shadow-r1/`

Create-once artifacts use atomic temporary-file publication, file fsync, atomic
rename, directory fsync, and SHA-256 readback through `tools/as003pr5_evidence.py`.

Phase A establishes exact baseline, `master` default branch, canonical Notion R5
authority, accepted predecessor manifests, protected scientific hashes, and zero
production change since the accepted baseline.

Pre-root prospective locks:

- common-root contract SHA-256: `d8d44647c914cf66eb260a07dcdb085f974e961cc5794ef58743c2c3f809a706`
- Habitat-root contract SHA-256: `0f68454e1b1a1d345770de796ef924ebc8ba80b12d759f31a912081a1a6101b4`
- parity source contract SHA-256: `fe4a6fa77e4a8d42a2b1841fc9f6bae11884ac89db83acc8c3814f89f13abcaa`
- comparator qualification SHA-256: `59c87995f3fe0de8c82075e5b9ba5c47bb657a4415e0ea879e5bbe6dd61c5e76`
- protocol preflight SHA-256: `c86ee8008eb7a44a3c284ccf3a09f2685b108c0fcfd807ee89fafb2191418ddc`
- comparator corpus: 24 cases, 2 deterministic runs, false positives/negatives `0/0`
- preflight counts: organism constructions/loads/ticks `0/0/0`

The exact interpreter established for the protocol is
`/home/sketch/cs14n-runtime/bin/python` (Python 3.12.3). Development attempts
with the absent `python` shim and system Python lacking pytest were environment
checks only; neither imported the fixture nor constructed an organism.
