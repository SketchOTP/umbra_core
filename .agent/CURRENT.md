# CURRENT.md

## Active directive
- ID: D-20260720-umbra-d000-track6-pepa-persistent-autonomy
- Project directive: UMBRA-D-000 (Track 6)
- Goal: Evaluate PEPA layered persistent autonomy; separate useful architecture from authored personality / LLM motivation
- Status: done
- Acceptance: Gates 0–11; PARTIAL_MECHANISM_QUALIFICATION; D-001 blocked — met
- Touched files: docs/prior-art/pepa/*, docs/evidence/d000-track6/*, SELECTION_LEDGER, .agent/*
- Next action: D-000 synthesis when operator opens — D-001 still blocked; Soar/Hyperon only if gaps remain

## Repo facts needed now
- Mimir project ID: 7777645d52a91b49
- Task ID: b707a36c6a6a47ffa8204aa730f3967c
- Track5 seal: 6bc8d81862d09558f3a62f4bcc4073aa2b3d64d7
- PEPA paper: arXiv 2603.00117v3
- Upstream: anonymous.4open.science BLOCKED (API 401)
- Verdict: UMBRA_D000_TRACK6_PARTIAL_MECHANISM_QUALIFICATION

## Last validation
- Command: `python3 -m pytest docs/prior-art/pepa/independent_reproduction/test_track6.py -q`
- Result: 19 passed; experiment seeds=30 ticks=10000
- Mimir: resolve + begin + compile + observe v3; close pending commit

## Open blockers
- D-001 remains blocked pending D-000 synthesis acceptance
- PEPA upstream code unreachable
