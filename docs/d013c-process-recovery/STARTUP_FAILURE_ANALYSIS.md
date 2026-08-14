# Startup failure analysis

The original generic `ORGANISM_START_FAILED: exit:1` was captured with replacement-worker stderr. The failure occurred after ownership acquisition and before the worker socket became ready:

`experiments/d012/organism_worker.py:134` → `umbra_core/runtime.py:2440 load_organism` → `umbra_core/persistence.py:352 Store.validate_chain` → `PersistenceError: ledger_tip_mismatch`.

The database was readable, so this was not an ownership or SQLite file-open failure.
