# Evidence

Fresh create-once evidence root:

`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r1-shadow-protocol-recovery/`

All durable artifacts use file fsync, atomic rename, directory fsync, and
readback SHA-256 verification. Scientific execution counts remain zero until
the exact command is frozen after a successful import-only preflight.

Phase A/B/C:

- state reconciliation: `PASS`, SHA-256
  `efc631b43eccdb1ce687ef4b0c716ac1dc6080be510813436a21b9aacefbd9e0`;
- original failure attribution:
  `REPOSITORY_ROOT_IMPORT_PATH_NOT_ESTABLISHED`, SHA-256
  `6a97dbe64a5934c9ee7fa04a8e71c8719c7e662e0056d5a865d88d49fa86c988`;
- protocol harness equivalence: `PASS`, zero scientific differences, SHA-256
  `82829ccc6696ac8348a33fec7019779ae9cf77dbf10badef66a95955d15c6835`.
- import-only preflight attempt 1: `PASS`; exact fixture, R1 harness, and
  `umbra_core` specs resolved from repository root; fixture preparation,
  organism create/load, harness `main`, leg execution, and ticks all `0`;
  SHA-256 `e94e8f17175a3b27e4570272cc2b820e717a201a08e4cd5bbbc06f9c1daaf426`.

Frozen execution:

- protocol lock: `b3364bc4e8fa08ccf006a6990866882676c845b3eee3b214feebdb5a64a2a14f`;
- pre-execution integrity: `PASS`, `41/41` focused pure, Authority 3.0 and
  governance `PASS`, SHA-256
  `7e6a4e250a76917f64026d91233f806ef9784f40ef6e69be2221fd4b3ea03e39`;
- exact command executed once; control/shadow `1/1`, each 500 ticks;
- parity PASS: timeline, candidate identities, RNG;
- parity FAIL: authoritative events, final authoritative state, subsystem
  hashes; unequal subsystem: WorldModel;
- raw capture: `500/500` complete frames, `2664` strong-MAY and `22` UNKNOWN
  profiles, zero candidate-profile distinctions; these are invalidated for
  scientific interpretation by observer failure;
- terminal verdict: `AS003PR1_OBSERVER_EFFECT_FAIL`; retries/reseeds `0/0`.

Closeout commit: `4d5f44ed8e9450516433d9820c5ad8b6517ee3c2`.
Final evidence manifest: 23 artifacts, readback verified, SHA-256
`a3e05489a73658cf02d10b3641671f515c4c2c498cd64b6ba0188bc1996159ab`.
