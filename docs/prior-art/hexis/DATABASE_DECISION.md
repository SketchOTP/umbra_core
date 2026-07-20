# Database decision

**Selected: `HYBRID_PRIMARY`**

Measured SQLite WAL: thousands of episodic writes, restart + backup on one file, zero daemons (`database-benchmark.json`).

Hexis PostgreSQL+AGE+pgvector: excellent multi-service cognitive server; migrations succeeded here; heavy for a standalone Linux pet.

Not chosen because Hexis calls Postgres “the brain.” Not chosen as SQLite-only forever — optional external indexes/scale tier allowed.

`POSTGRESQL_OPTIONAL_SCALE_TIER` remains available if multi-writer cloud appears later; primary companion authority should be embedded.
