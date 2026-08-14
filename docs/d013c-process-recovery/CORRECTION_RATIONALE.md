# Correction rationale

One minimal causal correction was made in `umbra_core/persistence.py`: `Store.append_event` now wraps the event insert and `meta.ledger_tip` update in one `BEGIN IMMEDIATE` transaction when no caller transaction is active, with rollback on failure. Existing outer transactions are preserved. No retry, sleep, threshold change, ownership weakening, chain-validation bypass, or architecture refactor was added.

The focused regression in `tests/test_d012_process_boundary.py` simulates failure exactly at the ledger-tip write and proves that the event insert is rolled back.
