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

Terminal retained evidence:

- shared root recovery SHA-256: `5761e4c928065dbc1da25ebe46ea1569c016bd668d8f541b60253078ca798bd7`
- root protocol failure SHA-256: `8c1ce6b4c4d678f8855603efa846836c4c5426987666c47987d84ba6412af9b8`
- scientific result SHA-256: `cf0a092c788fc1f90e11ad7be6cbeb43206aafd071731486515f1c1cedfd843a`
- root database integrity: `ok`; root snapshot sequence/state hash:
  `5 / 25f048b5bd6a6be67ac6a1c3d4e984407ec19ec25c3f099232c5102af5467051`
- root creation/ticks: `1/0`; CONTROL loads/ticks: `0/0`; SHADOW loads/ticks:
  `0/0`; retries/reseeds: `0/0`.
- root Habitat canonical SHA-256:
  `a6b918441342908673c80e1771e30dc1cb51020e716efe0d481fd40e693ed24b`
- root RNG SHA-256:
  `e2c69703d1fc3181bb62beaf9584410dfad02dba8141c3536198b0ce792aad68`
- append-only closeout correction SHA-256:
  `73f7b8358c8eb35c7be9fa438b42dd6a809f76b2f43f321f5430d513f45c4986`
- authoritative final readback manifest SHA-256:
  `1e1d36383a85cf95e84df4613dd324b7d8ab480d3462a8a593568e79efcd5b08`
