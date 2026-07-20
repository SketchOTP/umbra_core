# CURRENT.md

## Active directive
- ID: D-20260720-0942-umbra-d000-prior-art
- Project directive: UMBRA-D-000
- Goal: Land prior-art reproduction gate before D-001; correct blind-greenfield program stance
- Status: done (directive landed; reproduction work not yet executed)
- Acceptance: D-000 + ledger + D-001 blocks in profile/map/rules/AGENTS; PROJECT_GOAL unchanged — met for this landing task
- Touched files: `docs/directives/UMBRA-D-000-prior-art-reproduction.md`, `docs/prior-art/*`, `.agent/PROJECT_PROFILE.md`, `.agent/REPO_MAP.md`, `AGENTS.md`, `.cursor/rules/04-umbra-architecture.mdc`, `.cursor/rules/05-project-directives.mdc`, agent memory logs
- Next action: Execute D-000 tracks (MicroPsi → Hexis → AEROS → homeostatic RL → AERA → PEPA → ledger → revise D-001)

## Repo facts needed now
- PRODUCT SoT: `.agent/PROJECT_GOAL.md` (unchanged)
- Program SoT for sequencing: `docs/directives/UMBRA-D-000-prior-art-reproduction.md`
- D-001 blocked until selection ledger complete
- Mimir binding: UNBOUND

## Last validation
- Command: `test -f docs/directives/UMBRA-D-000-prior-art-reproduction.md`; rg gate language; PROJECT_GOAL md5
- Result: D000_OK; gates in AGENTS/profile/rules/map; PROJECT_GOAL `6fd509c0…` unchanged (35 lines)

## Open blockers
- Mimir register still UNBOUND
- D-000 reproduction tracks not started
- Operator should append UMBRA-D-000 to `.agent/RECORD.md` (agents must not edit RECORD)
