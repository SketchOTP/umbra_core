# D-013Q post-run validation

The runner-produced `P0_READONLY_POSTRUN_VALIDATION.json` is authoritative for
the formal execution's read-only closeout. It records:

- `validation_status`: `PASS`
- `chain_status`: `ok`
- `sqlite_integrity`: `ok`
- `mutating_api_used`: `false`
- `runtime_ready_count`: `1`
- `snapshot_count`: `2`
- `max_event_sequence`: `419`
- `formal_execution_id`: `d013q-formal-0d2ace2`

The exact formal baseline, contract fingerprint, and configuration fingerprint
match the frozen manifest. The historical D-012 and D-013L/D-013O evidence
paths were unchanged.
