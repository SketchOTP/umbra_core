# UMBRA-AS-003E evidence

- Baseline: `4b3b23c86cad8d93f523c67651b702e1111b5a05`.
- Frozen corpus only: AS-003C Diagnostic A/B decision traces and AS-003D analyses.
- AS-003C trace SHA-256: A `1d6825589f7e5102b98c15263d749d996b702f34fbdf347c824dc1870e249a2d`; B `ea576e9ef0050de56cb679c4d67937b913590d970d426e9115eb62731883a8b5`.
- AS-003D final manifest SHA-256: `b2a606286f6e197d100298e3e1d73031b1d302e0cccaacd0a9b3da2a9811cbfe`.
- All AS-003E durable artifacts must use file fsync, atomic rename, directory fsync, and readback SHA-256.
- Immutable pre-projection role lock: `AS003E_ROLE_CLASSIFICATION_LOCK.json`, SHA-256 `65b7d094c0ef99a2f68740fc91d6e9f0a91c4a6ec82bf126f61c24dd8ac6ec76`; role map SHA-256 `9bb173cc9a6e4187c270ff55053e8cc6e5a71dc704be243bf3cdcdbd9b3499b4`; channel audit SHA-256 `bbe332ccdd976b77435b4d1b766ed961fc2e9b4bc37894ce98897e822f43aa3a`.
- Final evidence manifest: `AS003E_EVIDENCE_MANIFEST.json`, SHA-256 `58c8cbcf4feb956cf52b936bc2b436494074a884bf0e2875326b00460efa47f7`; `15/15` required artifacts readback-hash match. Frozen role-partition projection: `0/76,216` relations, `0` eliminations, `2,647` full frontiers, `2,647` stochastic resolutions. Integrity: production/test changes 0; organism/diagnostic runs 0; retries/reseeds 0.
