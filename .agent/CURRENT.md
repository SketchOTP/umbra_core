# CURRENT.md

## Active directive
- ID: D-20260724-umbra-d010-temporal-continuity
- Project directive: UMBRA-D-010
- Goal: Temporal continuity (design → implement → seal)
- Status: design brainstorming — Decision A locked (TemporalEngine sole temporal authority)
- Acceptance: Design approved + plan + QUALIFIED only if Gates 0–15 pass
- Next action: Continue design questions; no temporal implementation until design+plan approved

## Locked design decisions
- **A — TemporalEngine sole durable temporal authority.** Runtime supplies trusted monotonic sample → `TemporalEngine.advance(...)` → committed `TemporalState`. `Runtime.tick` = orchestration sequence only. Age advances only on committed ticks; failed/rolled-back ticks do not advance age. Downtime via TemporalEngine. Immutable temporal views to other subsystems.

## Repo facts needed now
- Starting commit (pre-bootstrap): `bb90e6111f883f58cced7e71b7d452df7f072aa7`
- D-009 seal: `af35371` / `UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED`
- Parent Mimir: `9adf61b087ea4fa6a90a1c3bd401a9b3` (open until seal)
- Directive: `docs/directives/UMBRA-D-010-temporal-continuity.md`

## Last validation
- Command: Decision A recorded; bootstrap commit pending
- Result: —

## Open blockers
- Design not fully approved
