# D-010-R1 RSS root-cause diagnosis

**Directive:** UMBRA-D-010-R1 / `D-20260724-1607-d010-r1-rss-remediation`  
**Failed freeze preserved:** `3178815` / `d010-fe-stage-b-v5`  
**Failed verdict preserved:** `UMBRA_D010_PERFORMANCE_FAIL`  
**Harness:** `experiments/d010/run_rss_diagnosis.py` (production-unreachable)

## Classification

```text
A. A production structure retaining unbounded state
   TemporalEngine._committed_advance_ids (and sibling observation-plan set)
```

Secondary hardening (not root owner):

```text
D. Native arena trim after snapshot/WAL (D-002P pattern) — removes staircase jumps
```

POST_HOC registry: no FIFO eviction (would break pending anchors). Cleared on successful
POST_HOC commit; replace_state still resets.
## Evidence

### Formal campaign (immutable)

- P0/P1/P2 FAIL `sustained_segment_growth`; slopes ~1.9–2.1 MiB/h
- TemporalAdvanceRecord inflates DB (~19 MiB) but omit-advance ablation did **not** change RSS
- Accelerated 7200-tick probe: temporal slope ~1.5 vs no_temporal ~0.13

### Isolation

| Mode | Finding |
|------|---------|
| omit TemporalAdvanceRecord wire body | payload −67%, RSS unchanged |
| temporal_off | RSS slope collapses toward D-009 class |
| tracemalloc | `engine.py:221` retains growing `_committed_advance_ids` |
| bound advance-id set to latest only | expected RSS owner removed |

### Root-cause package

| Field | Value |
|-------|-------|
| root cause | Unbounded `_committed_advance_ids` grows one UUID string per tick |
| retaining owner | `TemporalEngine` in-process set (duplicate-commit guard) |
| reproduction | P0 soak or accelerated 7200 ticks with temporal enabled |
| measured contribution | Temporal on vs off ≈ +1.2 MiB / hour-equivalent; set size = tick count |
| affected files | `umbra_core/temporal/engine.py`; `umbra_core/runtime.py` (arena trim) |
| smallest corrective change | Replace set on commit with `{plan.advance_id}` only; FIFO-cap POST_HOC registry; arena trim after snapshot/WAL |
| expected regression risk | Low — `apply_advance_plan` already rejects `last_advance_id` reuse; ledger remains authoritative |

## Artifacts

- `docs/evidence/d010/rss-diagnosis/` (harness outputs + this note)
- Failed Task 14 evidence under `docs/evidence/d010/` **unchanged**
