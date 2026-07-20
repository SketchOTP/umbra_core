# Upstream reproduction

## Environment

- Built `ops/Dockerfile.db` → local image digest recorded in source-manifest.
- `docker compose up -d db` with disposable credentials (`hexis_user` / compose defaults).
- No messaging/email/browser/shell channels enabled (worker profile not started).
- Embedding sidecar (`host.docker.internal:11434`) **unavailable** on this host.

## Steps and results

| Step | Result |
|---|---|
| License validate | MIT; hash recorded |
| Build DB container | PASS |
| Start Postgres+AGE+pgvector image | PASS (healthy) |
| Migrations empty volume | PASS (init scripts through `91_triggers.sql`) |
| Upstream pytest | BLOCKED (`asyncpg` missing on host; not installed into product env) |
| Init test identity | PARTIAL (DB functions present; full `hexis init` / consent UI not run) |
| Memory create/retrieve | PASS after **in-DB mock** of `get_embedding`; FAIL against real embedding URL |
| Heartbeat path | Functions callable (`should_run_heartbeat`, `run_heartbeat`, `start_heartbeat`); returns null/false without configured agent/LLM loop |
| Stop workers | N/A (workers not started) |
| Restart DB | PASS — 2 memories preserved |
| Provider | deterministic SQL mock embedding |

## Isolation

Dedicated compose project `upstream`, volume `upstream_postgres_data`, bind address localhost. Teardown: `docker compose down -v` in `docs/prior-art/hexis/upstream`.

## Honesty

Full Hexis product loop (consent, character, LLM heartbeat worker, real embeddings) was **not** completed. Upstream execution is partial but non-vacuous.
