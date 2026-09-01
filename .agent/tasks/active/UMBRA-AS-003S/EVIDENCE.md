# Evidence

## Governance start

- Exact baseline/local master/GitHub master: `9cd69768c0cacc3a8a6955e35412d931c9f33f94`.
- Parent verdict: `AS003PR4_BODY_REPLACEMENT_IDENTITY_DEFECT_CONFIRMED`.
- Parent manifest SHA-256: `4e19d221647bf810418e7a961886a31fcd4432f8a882cb09cdeb0788b3de8864`.
- Protected results: `UMBRA_D008_COHERENT_DIGITAL_EMBODIMENT_QUALIFIED` and
  `UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED`.
- Planning observer work, integrated viability, AS-004, and CLOSE-03 remain blocked.

Further create-once evidence is published to the Atlas evidence root and summarized
here at closeout.

## Preimplementation locks

The replacement identity, event, occupancy, preflight, atomic persistence, and
crash-injection contracts are source-controlled beside this task packet and are
published create-once to the evidence root before production implementation.

- replacement identity: `ce849e52967ff605e8803a67507e35f65a7d4da46b1ed909c928d471d96becc8`
- replacement event: `6345ddf17a526596b0b42babbb511c728da29225b21eb3e774eb49d9c3960250`
- occupancy identity: `1512300f3859602b293873e5e177d032286e188ff536d0b28a8bdbd0d2429f62`
- replacement preflight: `152cd4cf59c5f62f5f2001e7ed27393639f22a2657f9cedfd73c183c6f0c67a3`
- atomic persistence: `f1d8ba011843f99701acadb309b3cbef0ae4d33ecc24230d6dc4e0c083e510fc`
- crash protocol: `3ea3249b78898db20cca72b28be0d047d5aee86cbe1d3d98fdec745612f1c4a8`

## Implementation and qualification

- Implementation commit: `39b509c82fc845bdee48803fc66d834adf39b487`.
- Focused replacement/crash/restart proofs: `14/14 PASS`; artifact SHA-256
  `eb2231b57c6105fc6b5e48d09e24296a4e5c277be3986d2c87b4c60262324b64`.
- D-002: `53 PASS / 1 FAIL`; identical failing node/assertion/value reproduced on
  exact baseline; artifact SHA-256
  `95ffe88b4bc77eea766549eb2f6e84af9d83ca483e595571e6b8694612cef6a9`.
- D-008/D-009: `202 PASS / 1 FAIL / 2 SKIP`; all D-008 pass and the D-009
  nonpass reproduces identically at baseline; artifact SHA-256
  `7a4b5d220b6940024f2c872cccdba71eedbb21741f8ab18ced169dde18ba66a6`.
- Path-safe applicable suite: `1120 PASS / 14 FAIL / 2 SKIP`; every current
  failing node exists at exact baseline, candidate-only failures `0`; SHA-256
  `d556c7af5854bfd096672ddf9f2cdeafa5d0d06ba2fbd2efb8125f49ca7b8cda`.
- Bounded lifecycle: one creation, one restart load, zero organism ticks, PASS;
  SHA-256 `fca17f949461d06e2a439349fa7644262dea8f9b8eb5db3771d5ca867bc1ab55`.
- Crash consistency proof SHA-256:
  `c292a2fa57ff71f5b0e2406c5fbec3ec3b46cf2942fdd5a946cd0d8c15ddd229`.
- End-goal audit SHA-256:
  `e109c2c1b29094e0ba3125d596051b7a56f3133229c7dd980d51699a02b7c0b9`.
- Authority 3.0, governance, governance negative fixtures, and `git diff --check`
  PASS; artifact SHA-256
  `d60ca7fcb734160ebf3ce4912a3553af3243858f6a0793aafafdc5c2ac301951`.
- Terminal verdict artifact SHA-256:
  `b1f3d729015bd7abd076c5ea04d7323aaab40dd662fad86217d0f88126268bd7`.

Qualification retries/reseeds `0/0`; observer and integrated-viability runs `0`.

## Final manifest

- Closeout commit: `99c95e4`.
- 18 pre-manifest artifacts plus one create-once manifest, all readback-verified.
- Manifest SHA-256:
  `6aaea514b0c829ca95b78ce76f440833f24ac30e61a6f4eab7ff7affa5d203bd`.
