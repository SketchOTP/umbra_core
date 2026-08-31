# UMBRA-AS-003F evidence

- Architect baseline: `7381af06a5a7b8b15e751f296cde18feec315585`.
- Frozen corpus only: AS-003C Diagnostic A/B traces and AS-003D/AS-003E analyses; qualified static fixtures may be inspected but never executed as organism/runtime tests.
- AS-003E final evidence manifest SHA-256: `58c8cbcf4feb956cf52b936bc2b436494074a884bf0e2875326b00460efa47f7`.
- AS-003D final evidence manifest SHA-256: `b2a606286f6e197d100298e3e1d73031b1d302e0cccaacd0a9b3da2a9811cbfe`.
- AS-003C final evidence manifest SHA-256: `d8eb4cc26048f6b3b8d9ca861dbfab25f56a6e2b95548949997c638f7812268c`.
- All AS-003F durable artifacts use file fsync, atomic rename, directory fsync, and SHA-256 readback.
- The activation/resolution lock must precede every offline context projection. No post-projection tuning is permitted.
