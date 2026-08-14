# UMBRA-D-013G

This dossier records the non-formal integration of `P0_RECOVERY_CONTRACT_V2` into the D-012 worker and runner path.

Scope is harness-only. No formal P0 was launched, no formal tag was created, and no `umbra_core/` behavior changed. Historical D-012 through D-013F results remain authoritative.

The V2 path now carries an explicit contract version and fingerprint, derives episode facts from live worker trace rows, records `P0_RECOVERY_EVALUATION_TRACE.jsonl`, and sends only integrity failures or causal repeated-denial failures to the runner's terminal boundary.
