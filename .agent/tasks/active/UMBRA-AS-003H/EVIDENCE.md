# UMBRA-AS-003H evidence

- Architect baseline: `b9f903d7954c922d2f52dd0a28762f91ccb22a54`.
- AS-003G manifest SHA-256: `ff78082a8982da6c11a2c403887c313dbd470f2cf24fbc9f8d1cbd3abaaead3e`.
- AS-003F manifest SHA-256: `2340788c8d1e2c19e2161831fdb6c1611f2aa6a85bd64afc77363971ff42c9dc`.
- AS-003E manifest SHA-256: `58c8cbcf4feb956cf52b936bc2b436494074a884bf0e2875326b00460efa47f7`.
- AS-003D manifest SHA-256: `b2a606286f6e197d100298e3e1d73031b1d302e0cccaacd0a9b3da2a9811cbfe`.
- AS-003C frozen corpus manifest SHA-256: `d8eb4cc26048f6b3b8d9ca861dbfab25f56a6e2b95548949997c638f7812268c`.
- All durable artifacts require file fsync, atomic rename, directory fsync, SHA-256 readback, and a final manifest.
- The transition proposition and learning-target lock must precede architecture projection.
