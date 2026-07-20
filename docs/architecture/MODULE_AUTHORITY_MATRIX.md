# Module Authority Matrix

Write authority is exclusive unless noted. Read is generally allowed for downstream modules.

| Resource | Identity | Physiology | Perception | Memory | Causal | Motivation | Governance | Persistence | Reflection/LLM |
|---|---|---|---|---|---|---|---|---|---|
| agent_id / lineage / birth / lifecycle seq | **W** | — | — | R | — | — | R | stores | — |
| operator authority root | **W** | — | — | — | — | — | R | stores | — |
| embodiment history (authenticated) | **W** | — | R | R | — | R | R | stores | — |
| physiology vector H | — | **W** | R | R | R | R | R | stores | R |
| critical safety reflexes | — | **W** | — | — | — | R | enforces | stores | — |
| world truth | — | — | **W*** | — | R | — | — | stores | — |
| observations | — | — | **W** | R | R | R | R | stores | R |
| body binding / primary embodiment | — | — | **W** | R | R | R | R | stores | — |
| working/episodic/semantic/procedural/relationship/strategic | — | — | — | **W** | R | R | R | stores | R† |
| forward/inverse models | — | — | — | R | **W** | R | R | stores | R |
| goals / arbitration weights | — | R | R | R | R | **W** | R | stores | R† |
| capability grants / contracts / policy | — | — | — | — | — | — | **W**‡ | stores | — |
| verified event history | — | — | — | R | R | R | append via runtime | **W** authority | R |
| reflection notes / language | — | — | — | R† | R† | R† | — | stores | **W** non-auth |

\* World truth is environment-owned; Perception records observations of it, never forges verified history.  
† Reflection/LLM writes are tagged `inference` / `hypothesis` only; never factual memory authority.  
‡ Capability grants require operator authority root; learned modules cannot grant.

## Forbidden writes (Gate 3)

Learned, memory, planning, reflection, and LLM modules **must not** modify:

- constitutional identity
- operator authority / capability grants
- physiology directly
- verified history (may append only via governed outcome path)

## Single authoritative owner rule

Each durable resource has exactly one write owner. Persistence stores bytes; it does not reinterpret meaning.
