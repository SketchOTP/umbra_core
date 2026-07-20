# State and Event Model

## Decision (required #4)

**Accepted:** Event ledger as causal authority + mutable materialised state as read-optimized projection.  
**Rejected:** Mutable-state-only as sole truth; Postgres-as-brain.

**Evidence:** Track 3 Hexis independent SQLite transactional continuity; `DATABASE_DECISION.md` → `HYBRID_PRIMARY`.  
**Tradeoff:** Dual representation requires projection rules.  
**Risk:** Projection drift.  
**Revisit:** Multi-writer cloud fleet requiring Postgres primary.

## Primary design

```text
SQLite WAL
  ├── events          (append-only, hash-linked)
  ├── state_snapshot  (materialised current)
  └── optional derived indexes
Optional later: PostgreSQL scale tier (not required for companion core)
```

## Event kinds (minimum)

- physiology_drift / physiology_effect
- observation
- memory_form / memory_correct / memory_supersede
- goal_commit / goal_abandon
- proposal / admission / denial
- execution / outcome_verified
- model_revise
- lifecycle / embodiment_bind / migrate / clone
- torpor_enter / torpor_exit
- capability_grant / capability_revoke (operator-signed)

## Mutable state

Holds current physiology, active goals, working memory, capability set, embodiment binding, model summaries. Always recoverable from events via deterministic replay (D-001 requirement).

## Survival requirements

State must survive process restart, model replacement, body replacement, capability upgrade, authenticated migration (Tracks 3–4).

## Rollback

Rollback restores a prior snapshot **or** replays events to a checkpoint. Rollback is an operator lifecycle action, not organism learning. Clone ≠ rollback ≠ migration (see `IDENTITY_AND_LIFECYCLE.md`).
