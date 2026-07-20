# CURRENT.md

## Active directive
- ID: D-20260720-umbra-d000-track5-aera-causal-learning
- Project directive: UMBRA-D-000 (Track 5)
- Goal: Reproduce/classify AERA cumulative causal learning & interruptible planning
- Status: done
- Acceptance: Gates 0–11; PARTIAL_MECHANISM_QUALIFICATION; D-001 blocked — met
- Touched files: docs/prior-art/aera/*, docs/evidence/d000-track5/*, SELECTION_LEDGER, .agent/*
- Next action: D-000 Track 6 (PEPA / Soar-Hyperon if needed) when operator opens — not auto-authorized

## Repo facts needed now
- Mimir project ID: 7777645d52a91b49
- Task ID: db45eb4295134a32b2c65a8fddd03ee5
- Track4 seal: d4df38bd51b2ca3ccc0615a74b808b02595992f3
- AERA pin: 77b570226d12052828ff5b7ee0ca968bf1702221 (CADIA reference-only)
- Verdict: UMBRA_D000_TRACK5_PARTIAL_MECHANISM_QUALIFICATION

## Last validation
- Command: `python3 -m pytest docs/prior-art/aera/independent_reproduction/test_track5.py -q`
- Result: 20 passed; experiment seeds=30
- Mimir validation_run: not used (local evidence)
- Upstream: container cmake PASS / compile FAIL; examples attempted without binary

## Open blockers
- D-001 remains blocked
- Track 6 incomplete
- AERA upstream binary not runnable on this host
