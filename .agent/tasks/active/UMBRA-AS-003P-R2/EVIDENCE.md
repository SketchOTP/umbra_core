# Evidence

Fresh create-once evidence root:

`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r2-observer-forensics-r1/`

All durable artifacts use file fsync, atomic rename, directory fsync, and
readback SHA-256 verification. Organism/control/shadow/diagnostic execution,
retries, and reseeds remain zero throughout this directive.

Governance start:

- state reconciliation: `PASS`, SHA-256
  `0e383b847341dc53f35cc42086edf295748d55cf175b410b079c5a637d16dcc6`;
- immutable H1-H5 attribution lock: SHA-256
  `ccfbe8c171f3be2ddf94360172381c0185108f15a36553289c1aad5b8ca5d118`.

Forensic results:

- comparator invariance proof: four synthetic false positives, SHA-256
  `35dbd599f66f19d4dd43013cf893a1165abb10df233d4d83a3b394eb946e30bb`;
- WorldModel semantic diff: exact model semantics and accepted-state equality,
  SHA-256
  `3cb61beb21237a937162d82b505646976e86e5ecf427a52e1f676f7ffa5d0467`;
- WorldModel relationship audit: all relationship-bearing fields equal after
  semantic-model labeling, SHA-256
  `770bef9124558145f233e13735df14070b7bf703158dd99b7f5958bdcd7a0217`;
- event semantic diff: only 2,500 source-proven derivative-hash leaves,
  semantic differences zero, SHA-256
  `4eb5dd0e67eefaa95c9d4b5085a89b99521d63d7c558df457ff50f958195cead`;
- final-state semantic diff: all subsystems semantic-equal, SHA-256
  `b4d699257c989b67cf1071372993ba92437e689728e4f284a6e1b608bef443cc`;
- first divergence: tick 1 derivative-hash-only, no semantic divergence, SHA-256
  `e1d863e86305fd44fdd5d01214885fcabaa8f656937f55bcf1597fedafd3d6ac`;
- shadow read-purity audit PASS, SHA-256
  `713277d184637781174fca98b624e646319ba1924e3a4e1d1569ffd322bdf30c`;
- pure proof 9/9 PASS (the initially selected system interpreter had no pytest
  and collected zero tests), successor interpreter command recorded; prior
  8/8 proof artifact SHA-256
  `5ff1d02f9b1071c7350fa67808f58606d4032d7143dc32e63d929294d51b9cca`.

Terminal verdict:
`AS003PR2_COMPARATOR_FALSE_POSITIVE_CONFIRMED`. R2 organism/control/shadow/
diagnostic executions, retries, reseeds, and production changes remain zero.
