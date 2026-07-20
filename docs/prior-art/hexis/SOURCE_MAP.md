# Source map (claims → implementation)

| Mechanism | Documented claim | Actual source | Authoritative state owner | LLM dep | Embedding dep | Graph dep | Scheduler dep | Mutation path | Transaction boundary | Audit path | Failure | Recovery |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Typed memories | five layers + worldview/goal | `db/00_tables.sql` enum; `create_*` in `db/05_functions_provenance_trust.sql`; `core/cognitive_memory_api.py` | PostgreSQL `memories` / `working_memory` | formation sweep yes | create_memory calls get_embedding | AGE MemoryNode on create | n/a | SQL create_* / CognitiveMemory.remember | DB transaction | source_attribution / trust | embedding outage blocks writes | retry embedding |
| Working memory | UNLOGGED TTL buffer | `working_memory` UNLOGGED; `hold()` | Postgres UNLOGGED | no | via add_to_working_memory | no | expiry | add_to_working_memory | weak durability intentional | limited | loss OK | recreate |
| Belief revision | support/contradict confidence | `db/05` + `59_belief_revision.sql` | Postgres | LLM may propose | search yes | CONTRADICTS edges | reconsolidation tasks | SQL revision fns | ACID | history/audit tables | contest vs apply | protected memories flag |
| Heartbeat | autonomous OODA + energy | `db/07_functions_heartbeat.sql`, `db/11_functions_core_heartbeat.sql`, `core/state.py`, `core/agent_loop.py` | Postgres state/energy/goals | **yes** for decide/act content | context hydrate | self/relationship graph | should_run_heartbeat / workers | run_heartbeat / worker | DB claims | heartbeat/outbox | null if unconfigured; energy gate | worker restart; DB authority |
| Identity/worldview | Big Five + worldview memories | `docs/concepts/identity-and-worldview.md`; `characters/*.json`; worldview type | Postgres memories + config | reflection yes | yes | self edges | subconscious | worldview writes | ACID | consent_log | consent decline blocks | restore DB |
| Workers | stateless | README; `ops/Dockerfile.worker` | DB | yes | sidecar | AGE | RabbitMQ/sched | workers poll DB | DB | tool audit tables | crash loses in-flight only | reclaim via DB |
| Self-termination | right to end existence | `is_self_termination_enabled`; character lore | Postgres lifecycle | yes to decide | n/a | n/a | n/a | termination fns | ACID wipe | last-will memory | irreversible | none (by design) |

Do not infer from filenames alone — create paths and heartbeat confirmed in SQL; Python API wraps SQL.
