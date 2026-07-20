# CURRENT.md

## Active directive
- ID: D-20260720-umbra-d000-track3-hexis-continuity-memory
- Project directive: UMBRA-D-000 (Track 3)
- Goal: Reproduce/classify Hexis persistence, memory, identity
- Status: done
- Acceptance: Gates 0–15; PARTIAL_MECHANISM_QUALIFICATION; D-001 blocked — met
- Touched files: docs/prior-art/hexis/*, docs/evidence/d000-track3/*, SELECTION_LEDGER, .agent/*
- Next action: D-000 Track 4 (AEROS) when operator opens — not auto-authorized

## Repo facts needed now
- Mimir project ID: 7777645d52a91b49
- Task ID: 4fa16223ae04432383a67461561de649
- Track2 seal: 12b354695079c7bd7e9cc85f2856bb5e56e73aa3
- Hexis pin: 50f5194da6b938e54ab87796ffc33d429b78bd89 (MIT 1.0.5)
- Verdict: UMBRA_D000_TRACK3_PARTIAL_MECHANISM_QUALIFICATION
- DB decision: HYBRID_PRIMARY

## Last validation
- Command: `python3 -m pytest docs/prior-art/hexis/independent_reproduction/test_track3.py -q`
- Result: 35 passed

## Open blockers
- D-001 remains blocked
- Tracks 4–6 incomplete
- Operator RECORD entries requested (companion-core + Track2 + Track3)
