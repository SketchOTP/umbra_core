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

## Pretreatment fork gate

- Exactly two SQLite backups and two Habitat copies derive from the retained root; semantic inventories equal, database/Habitat inodes independent, shared writable WAL/SHM absent, retained source hashes unchanged. Clone proof SHA-256 `65e438f92619d71efcec4423bfccbff20fab5ca060cc486e600d45970840a5e6`.
- Branch loads: CONTROL `1`, SHADOW `1`; measured ticks `0/0` at barrier.
- Premeasurement parity: PASS; semantic differences `0`, administrative differences `2`, derivative differences `1`; SHA-256 `c2a0d117f35be987e7a14d829a6476b8b5fdf2c01abb6375b7e4518b58d09bb2`.
- Frozen interpreter/command: `/home/sketch/cs14n-runtime/bin/python -m experiments.as003pr5a.common_root_pair orchestrate`, repository-root working directory, retained seed `45878900`, horizon `500`, retries/reseeds `0/0`.

## Frozen paired execution and interpretation

- Execution: exactly one CONTROL and one SHADOW leg; measured ticks `500/500`; retries/reseeds `0/0`; exit status `0`.
- Semantic parity: PASS; semantic differences `0`; first divergence `NONE`; timeline, candidate identities, authoritative events, final authoritative state, Habitat, and RNG equal. Administrative differences `4,888` and derivative differences `10,628` remain explicitly non-semantic under the prospectively frozen comparator.
- Actual frames: attempted/complete/rejected `500/500/0`; capture/evaluation errors `0`; candidate profiles `2,686`.
- Modal distribution: `STRONG_MUST 0`, `STRONG_MAY 2,664`, `WEAK_MAY 0`, `NO_CONTINUATION 0`, `UNKNOWN 22`; branch-frontier peak `4`, overflow `0`.
- Distinctions: frames with candidate-profile distinctions `0`; candidate pairs with distinctions `0`.
- Exposure: 59 ordinary multi-drive conflict decisions; 57 satisfy the complete AS-003L residual-conflict exposure definition; exposed decisions with profile distinctions `0`.
- AS-003L: `BLOCKER_NOT_EXPRESSED_DESPITE_EXPOSURE`.
- AS-002 future boundary: `NO_RELATION_SUPPORTED`; epistemic strength was not treated as preference.
- Historical R1/R3/R5 modal counts used: `false`.
- Terminal verdict: `AS003PR5A_OBSERVER_SAFE_MODAL_EVIDENCE_NONDISCRIMINATING`.
- Authority 3.0, governance, `git diff --check`, retained-root readback, and 84-link public navigation validation: PASS.
- Closeout SHA-256: `37b83cf2b139f8d1a284e733507156e508ed2d5c5a9e346e3064da5809ec1a72`.
- Final manifest SHA-256: `271a717821c07defbc0b5b89191065f0e5923e60bbd71dac0855fd45ecebb805` (`38` inventoried artifacts plus manifest).
