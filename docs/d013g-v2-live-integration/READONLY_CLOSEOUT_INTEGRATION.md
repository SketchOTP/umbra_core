# Read-only closeout integration

The future V2 runner closeout calls `validate_read_only()` only after worker shutdown. The validator opens SQLite with `mode=ro` and `PRAGMA query_only=ON`, and does not call `Store`, `load_organism`, schema initialization, migration, or `runtime_ready` APIs.

The existing disposable database mutation proof remains part of the D-013F suite. D-013G also covers the runner hook and its artifact name.
