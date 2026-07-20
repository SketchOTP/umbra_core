# Source map

| Mechanism | Claim | Actual source | Authority owner | LLM dep | Audit | Failure |
|---|---|---|---|---|---|---|
| Identity hash | Stable across upgrades | `runtime/persona_*.py`, MCP identity tool | IdentityManifest + PersonaCore hash | no for hash | persona adaptation chain | drift detect |
| PersonaCore | Frozen operator commitments | `persona_core.py` | Hashed into identity | no | n/a | must not auto-mutate |
| PersonaAdaptive | Lived calibration | `persona_adaptive.py` | Outside identity hash | optional emitters | signed events | HR-6 reject |
| Policy engine | L1 override / L2 ECM / L3 risk | `governance/policy/engine.py` | PolicyEngine | no | GovernanceAuditLog | deny |
| Runtime gateway | Policy then execute | `runtime_gateway.py` | gateway | no | audit record | deny/crash |
| Contracts | Semver interface | `governance/contracts/` | checker | no | n/a | incompatible block |
| Evolution | Shadow/canary/rollback | `evolution/` | gated publisher | no | evolution audit store | rollback |
| ECM lifecycle | install/activate | `ecm/lifecycle.py` | registry | no | sandbox audit | validate fail |
| Migration | .aer bundles | `cli/migrate.py` | operator | no | verify | reject |
| Audit chain | cause-id + Ed25519 | `audit/chain.py` | trusted keys | no | verify_chain | fail closed |
