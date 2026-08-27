# UMBRA-CLOSE-02-DECIDE

Status: ACTIVE

Purpose: determine whether the CLOSE-02 final-authority change caused the
CLOSE-02F R0/S0 failure for seed 45878900.

The diagnostic compares one isolated pre-CLOSE-02 control at
178f0e37855c42a3b97975189b7700b5b16b7506 with one isolated final-authority
candidate at 20542be24c90317aefbb0df9cfdc2202b9d8942b. Both use the same R0/S0
configuration, seed, and 7200-tick horizon. Instrumentation is observational
only; no source checkout is modified.

1. Freeze source/configuration and evidence manifest.
2. Prove instrumentation parity, then run A and B exactly once.
3. Align traces, classify attribution, validate, and close out.

