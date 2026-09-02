# Evidence

## Starting authority

- Exact baseline: `04946e3fc977593bf41d1eb40f1fc8517ef289aa`
- Parent verdict: `AS003PR5_PROTOCOL_PREFLIGHT_FAIL` (permanent)
- R5 comparator/source lock: `14d9ce3252701d95e840bad6e28b0efd17e6cdd4`
- R5 corrected readback manifest: `1e1d36383a85cf95e84df4613dd324b7d8ab480d3462a8a593568e79efcd5b08`
- R5A root creation policy: `0`
- Retained root: R5 `r5-work/shared-root.sqlite` and `shared-habitat.pickle`
- R5A evidence root: `/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r5a-retained-root-modal-shadow-r1/`

Evidence results are appended as gates complete. No R5 artifact is overwritten.

## Pre-branch gates

- State reconciliation: PASS; governance start `f6723b2`; canonical Notion start heading refetched exactly.
- Metadata preflight: 8/8 synthetic cases PASS; organism creations/loads/ticks `0/0/0`; evidence SHA-256 `82428000e40e7bd1bc0f19fb97e534e4713aaabb7b5d069b83635ae0d012b1bb`.
- Retained root: SQLite `ok`; ledger `5` events; raw snapshot `a580866c-56e0-4fc0-94a5-8bfe70256e22`; sequence/hash `5 / 25f048b5bd6a6be67ac6a1c3d4e984407ec19ec25c3f099232c5102af5467051`; RNG `e2c69703d1fc3181bb62beaf9584410dfad02dba8141c3536198b0ce792aad68`; Habitat `a6b918441342908673c80e1771e30dc1cb51020e716efe0d481fd40e693ed24b`; all retained file hashes unchanged.
- Attestation correction: the first create-once R5A attestation used a newline in its RNG hash input. It remains preserved; authoritative append-only correction SHA-256 `619606dcbdbcc1d700494f50ee98d9f491f55b2c731b8199c4e34140a176efec` records the correct R5 convention and confirms root bytes did not change.
- Comparator inheritance: six frozen files BYTE_IDENTICAL to `14d9ce3252701d95e840bad6e28b0efd17e6cdd4`; 24-case corpus twice, false positives/negatives `0/0`; evidence SHA-256 `60c9d2d2a913b439303c1ec2721ec60d5867f23c542d809c58e60eff7ff0ac01`.
- Clone protocol SHA-256: `4466ac3c490d2e0fdb2d30bd1a39d23e918fbf76725bcd395d5c0659bdcb67b4`.
- Fresh harness import/static preflight: PASS; no `fixture.prepare()` call, fresh work root absent, required evidence present, organism creations/loads/ticks `0/0/0`; evidence SHA-256 `36fc07e35bd1ba2d7a5115b563f464fd9db7ad31fa44f2b71567d87c08e26063`.
