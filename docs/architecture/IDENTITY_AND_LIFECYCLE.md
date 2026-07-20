# Identity and Lifecycle

## Constitutional identity owns

- `agent_id` (stable unique)
- lineage (parent/clone graph edges if any)
- birth record (timestamp, operator, genesis hash)
- lifecycle sequence (monotonic signed transitions)
- operator authority root
- authenticated embodiment history

## Constitutional identity excludes

personality; memories; model identity; body identity; skills; mood; preferences.

Evidence: Track 4 identity tests; PROJECT_GOAL success criterion 1.

## Commitment model (decision #6)

Identity is a **signed constitutional record** bound to the event ledger genesis. Changing excluded fields does not mint a new agent. Changing constitutional fields requires operator-authorized lifecycle transition.

## Body migration (decision #7)

**Migration:** same `agent_id`; new embodiment binding; single-use migration token; history preserved.  
**Clone:** new `agent_id`; optional copied non-constitutional state; lineage edge to source; distinct individual.

Evidence: Track 4 clone vs migration.

## Capability lifecycle (decision #8)

Capabilities are versioned contracts, granted/revoked only under operator authority + governance. Upgrade ≠ developmental learning (Track 4 REJECT). Shadow/canary/rollback allowed for capability packages, not for rewriting history.

## Continuity semantics

| Event | Identity | History | Physiology | Memory | Caps |
|---|---|---|---|---|---|
| Process restart | same | same | restore | restore | same |
| Model replacement | same | same | same | same | same |
| Body migration | same | same + bind event | same | same | re-check body contracts |
| Capability upgrade | same | upgrade event | same | same | new versions |
| Clone | **new** | optional copy tagged | copy or reset | optional copy | re-grant |
| Rollback | same | truncated/fork policy explicit | restored | restored | restored |
| Corruption | same if salvageable | quarantine bad segments | safe defaults / torpor | rebuild from events | freeze grants |

## Failure / safe-torpor (decision #18)

On ledger corruption or critical physiology without recovery path: enter safe-torpor; refuse consequential actions; require operator salvage or replay-from-last-good.
