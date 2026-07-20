# Memory architecture (Hexis → UMBRA)

## Hexis

- Durable types in `memories`: episodic, semantic, procedural, strategic, worldview, goal.
- Separate UNLOGGED `working_memory`.
- Vector embeddings on write; AGE graph nodes/edges; neighborhoods; reconsolidation tasks.
- Belief confidence with sources; contradictions as edges; protected/origin memories.

## Independent contract reproduction

SQLite package mirrors **contracts**: working TTL/capacity, immutable episodes, semantic support/contradict/supersede, procedural success/failure, strategic non-authority, provenance traces — without Postgres/AGE/LLM.

## UMBRA stance

**ADAPT** typed memories + provenance + supersession. **REJECT** treating embeddings or LLM salience as the only gate to existence of memory. Memory must remain valid when embedding/LLM are down.
