# CURRENT.md

## Active directive
- ID: D-20260720-umbra-d000-track4-aeros-governed-individual
- Project directive: UMBRA-D-000 (Track 4)
- Goal: Reproduce/classify AEROS identity, capability, governance, embodiment
- Status: done
- Acceptance: Gates 0–16; PARTIAL_MECHANISM_QUALIFICATION; D-001 blocked — met
- Touched files: docs/prior-art/aeros/*, docs/evidence/d000-track4/*, SELECTION_LEDGER, .agent/*
- Next action: D-000 Track 5 (AERA) when operator opens — not auto-authorized

## Repo facts needed now
- Mimir project ID: 7777645d52a91b49
- Task ID: 35b14ff4ca9748c68e7d57c5f5415f18
- Track3 seal: bdc2b9a661816afe6b9c702313c81b6876f07b60
- aeros-core pin: 3e46d82bf5cd829df8d00061b865b7eb709e278d (AGPL 0.15.0)
- historical aeros: f3a5ef0d976fadc78e3914b23af55ac532b7d2e5
- Verdict: UMBRA_D000_TRACK4_PARTIAL_MECHANISM_QUALIFICATION

## Last validation
- Command: `python3 -m pytest docs/prior-art/aeros/independent_reproduction/test_track4.py -q`
- Result: 69 passed
- Mimir validation_run: BLOCKED (server: active observed task / allowlist); local evidence used
- Mimir task close: 35b14ff4ca9748c68e7d57c5f5415f18 v3 completed

## Open blockers
- D-001 remains blocked
- Tracks 5–6 incomplete
