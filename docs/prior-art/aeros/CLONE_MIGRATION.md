# Clone vs migration

| | Migration | Clone |
|---|---|---|
| agent_id | preserved | **new** |
| lineage | same individual | child lineage = parent agent_id |
| token | single-use; duplicate rejected | n/a |
| split-brain | stale host / duplicate live claim fail-closed | two lives after fork event |

Backup restore with lifecycle < current → FAIL_CLOSED.
