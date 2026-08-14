# UMBRA-D-013C process recovery diagnosis

Verdict: `D013C_PROCESS_RECOVERY_CORRECTION_PASS`.

The exact D-013B `[False]` test passed on its first isolated rerun and five repeats, so the original failure was not deterministic at the test level. A bounded diagnostic harness then reproduced the failure once in three ordinary-SIGTERM attempts and zero of three SIGKILL attempts. The captured generation-2 exception was `PersistenceError: ledger_tip_mismatch` in `umbra_core/persistence.py:352`.

The failed database had a valid SQLite integrity check and a valid event hash chain through sequence 11, but `meta.ledger_tip` still named sequence 10. The single correction makes the event insert and ledger-tip update one transaction. No formal P0 was launched, D-013B remains `D013B_PREFLIGHT_FAIL`, and the old formal tag was not changed.
