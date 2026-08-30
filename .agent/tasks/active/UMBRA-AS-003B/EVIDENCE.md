# UMBRA-AS-003B evidence

- Permanent root: `/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003b-fresh-distributed-competition-r1/`
- Start master: `adeb4cf746a6e6bb4baf7a171017708e707c8001`
- Production candidate comparison: current `umbra_core/` is identical to `c266318229ae3759f80ac8958ecf63e8a2ab5468`.
- AS-002 manifest: `55bbd19714c0549fb516926ee8dcc60cbd488d338c8a45e1dab8e48343f4ab2c`.
- AS-003 manifest: `7a4c77c50eb2395a0cc97bdedc290221c0ab9035cdf1700d5b53ba48b4b23985`.
- AS-003A manifest: `23e0c8bcdd3ba64ff6f60da46ba9f8a4f46fb62369788b26f17da16b1bc5afe0`.
- Immutable AS-003B evidence policy: `AS003B_EVIDENCE_POLICY.json`, SHA-256 `54765d562196b74b4d9f7fb27bbb31d81ba39a1539a9a68a1d489fc2aa4ffcd2`.
- Pre-freeze contract audit: `AS003B_CONTRACT_CONFORMANCE_PRE_FREEZE.json`, SHA-256 `d6e374e12a0fde1849f2fbfaae85acb7e6dcb3c8b7b11d406fe947d1cb750c20`.
- Scope/scalar audit: `AS003B_SCOPE_AND_SCALAR_AUDIT.json`, SHA-256 `6f2bb2af014545142e990a87c4ea7ca5630e5de9e7efa2f7b0e41afc46b31098`.
- Completeness map: `AS003B_COMPLETENESS_MAP.json`, SHA-256 `79865cf2f8c4e213a303e6ffe4a79779c1cc1cdce50b1cdc347cfaea6d072a83`.
- Frozen pure-test allowlist: `AS003B_PRE_FREEZE_PURE_TEST_ALLOWLIST.json`, SHA-256 `c3ddb102c98731bd2a6aa9ffdb74d5e5dc2c19b03be5919131dee1f954ece85b`.
- No post-freeze result may be summarized without command, node list, output, JUnit/XML, and SHA-256 evidence.
- Bounded production correction: `074376d48cde4c55db38ddf8adec9d40c92bf4f6`; external correction record SHA-256 `081d11642341d5b3fa1638cd9d89f60843c9609c0330d0c5d3e6b31e6363cb64`.
- Revision-2 pure allowlist: SHA-256 `5b96f55ff4d14bb151fcd3f749b4d5b6a9c1044aad92534338835cc7b032efd1`; proofs: execution 001 `14/14 PASS`, execution 002 `3/3 PASS`, zero organism/runtime entries.
- Non-production frozen-command support commit: `39aa00e0f2e4b5694141366da700fd976e10493c`; it leaves the production tree fingerprint `ed5eaf31edac7365aa048b5382b4774b2c206ec03fdfecd710d322c8677cbb51` unchanged.
- Pre-freeze manifest: `AS003B_PREFREEZE_EVIDENCE_MANIFEST.json`; it indexes every audit/proof plus the frozen diagnostic/capture/test-selection support. Status: pre-freeze ready, not frozen.
- Freeze: `5c2642ac9c1c0be6340d583caf594f5799ecda13`. Frozen retained replay: `57 PASS / 1 FAIL`; durable command/JUnit/per-test evidence begins `AS003B_RETAINED_REPLAY.*`. Terminal record: `AS003B_TERMINAL_RESULT.json`. No later post-freeze command ran.
- Final evidence manifest: `AS003B_EVIDENCE_MANIFEST.json`, SHA-256 `a5c914980f877fca195ab70aa3816abaeba22fbf7bb6b4596987b153b3810a70`; parse/readback PASS.
