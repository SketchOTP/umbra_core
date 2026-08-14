# Persistence analysis

On the captured failed database, `PRAGMA integrity_check` returned `ok`; the database was readable; WAL and SHM were absent after observation; events were present and hash-linked through sequence 11; the latest snapshot was sequence 3 and its JSON/hash were valid. The only inconsistency was `meta.ledger_tip`, which remained at sequence 10 while the event table contained sequence 11. `load_organism` correctly failed closed on that mismatch.
