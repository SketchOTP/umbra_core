# Contract selection

The worker manifest carries `formal_recovery_contract_version`.

- `P0_RECOVERY_CONTRACT_V1` preserves historical D-012 behavior and requires no V2 fingerprint.
- `P0_RECOVERY_CONTRACT_V2` requires fingerprint `511c6f56d1cde7c5c28e290e7b1679eea85494b642eb57b5642a5295bbdd2ad2`.

Unknown versions, missing V2 fingerprints, and incorrect V2 fingerprints are rejected. V2 never silently falls back to V1.
