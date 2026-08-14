# V1 compatibility

The same D-013D-like denied CHARGE row produces `charge_selected_but_not_executable` under `P0_RECOVERY_CONTRACT_V1`.

The same row produces `SAFE_DENIED_RECOVERY_ATTEMPT` and no terminal failure under V2. This compatibility behavior is covered by the non-formal live worker integration tests.
