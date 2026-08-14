# Read-only post-run validation

`experiments/d012/readonly_validation.py` opens SQLite with URI `mode=ro` and
does not instantiate `Store`, `load_organism`, schema initialization,
migrations, snapshots, ownership changes, or `runtime_ready` emission.

It validates SQLite integrity, identity commitment, event sequence and hash
chain, ledger tip, snapshot hashes, and terminal runtime-ready count. The
regression test hashes a database and compares event count, ledger tip,
snapshot count, runtime-ready count, and file hash after validation.
