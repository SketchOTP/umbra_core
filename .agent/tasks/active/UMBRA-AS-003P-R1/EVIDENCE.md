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
