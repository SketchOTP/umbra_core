# Evidence

Fresh create-once evidence root:

`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r3-semantic-shadow-pair-r1/`

All durable artifacts use file fsync, atomic rename, directory fsync, and
readback SHA-256 verification. Before the comparator/execution lock, organism,
control, shadow, and diagnostic executions remain zero.

Comparator qualification:

- source contract SHA-256: `b488b22865f5f9789ad33a8143f46d04b6b8ebd62170c0e0fba707886e1f83d8`;
- adversarial corpus SHA-256: `f0bd96e6e4c43cad876c3b7ce3699066b89cf8612a9c789913b99058c8623d2b`;
- comparator source SHA-256: `596ab86f41523ea16dde44693b5aa7a702f0514fc38c18717aa0070c1590da66`;
- qualification: 28 locked cases plus two completeness/reporting checks,
  `30/30 PASS` twice locally and once on Atlas, false positives `0`, false
  negatives `0`, deleted cases `0`;
- qualification evidence SHA-256:
  `57a3529372622e7a1868332cb17e4a1e3486575287259c3ca3f965cfb08e1fb7`.

Execution:

- comparator lock commit: `e1e617b63940d611120068b4fb3b1fc2d7323ddf`;
- frozen execution commit: `fa68dd6e785ce2c45840306b65cbb313d2b17cb9`;
- control/shadow executions: `1/1`, 500 ticks each; retries/reseeds `0/0`;
- semantic observer parity: FAIL, semantic differences `2`;
- differing paths: `authoritative_events.1.payload.new_body_instance_id` and `final_authoritative_state.embodiment_adapter.body_instance_id`;
- administrative/derivative differences: `4,891 / 10,643`, reported separately;
- timeline, candidate identities, and RNG: equal;
- planning trace retained, but modal interpretation and conflict-exposure analysis: NOT REACHED.
