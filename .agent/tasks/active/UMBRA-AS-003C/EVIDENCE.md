# UMBRA-AS-003C evidence

- Start master: `327f747612626e3894192879ce961489e9308d6a`.
- Parent terminal evidence: AS-003B manifest SHA-256 `a5c914980f877fca195ab70aa3816abaeba22fbf7bb6b4596987b153b3810a70`.
- AS-003B freeze: `5c2642ac9c1c0be6340d583caf594f5799ecda13`; current production diff is empty.
- Evidence root: `/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003c-replay-migration-qualification-r1/`.
- Every post-freeze command must retain raw output, JUnit XML when pytest is involved, individual test records, and SHA-256 inventory.
- Replay semantic audit: `AS003C_REPLAY_SEMANTIC_AUDIT.json`, 56 replay tests classified; exactly one property-valid migration required; SHA-256 `358c6783c6a2cee9d28d3730596c55435dcb084e04a9a0368b33dde35bb7e354`.
- Migration manifest: `AS003C_TEST_MIGRATION_MANIFEST.json`, one scalar-winner assertion replaced by a no-intent base-authority property; SHA-256 `efda08303fd0cd89726e402e9b14ff94afeb6a23a343c35bc6c0e9dfb3f77460`.
- Pure allowlist: 56 explicit source-proven nodes; executed result `58 PASS` including parameter variants, no organism/runtime entry; command evidence SHA-256 `e518c333f5bc6298589c3fafbcb0ab0dccaa401bba1aa75978673902b05f0f1a`.
- Production immutability, contract, scope/scalar, and completeness audits PASS; no production delta from AS-003B freeze.
- Dedicated freeze: `e336c25064dd87b7a71966f034ba317fa7cb6116`; production fingerprint `ed5eaf31edac7365aa048b5382b4774b2c206ec03fdfecd710d322c8677cbb51`.
- Frozen replay: `58 PASS / 0 FAIL`, command SHA-256 `19392a0d30aaaeaaa25101b037518a4540344207d5aceffd6b375c95456057bc`.
- Diagnostics: A `500/500 PASS`, B `3500/3500 PASS`; frozen traces show 2,647 qualifying decisions, 0 dominance eliminations, and 2,647 full frontiers.
- Terminal result: `AS003C_DOMINANCE_NOT_REALIZED`; secondary `AS003C_FRONTIER_SATURATION_FAIL`. Final evidence manifest SHA-256 `d8eb4cc26048f6b3b8d9ca861dbfab25f56a6e2b95548949997c638f7812268c`.
