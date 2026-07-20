# CURRENT.md

## Active directive
- ID: D-20260720-1032-umbra-d000-track2-seal
- Project directive: UMBRA-D-000 (Track 2 seal → Track 3 gate)
- Goal: Commit Track 2 evidence; clean worktree; recompute hashes; Mimir outcome with final commit
- Status: in_progress
- Acceptance: track2 commit; worktree clean; evidence hashes from commit; Mimir closed against commit; track2-seal.json ready for Track 3
- Touched files: docs/prior-art/homeostatic-rl/*, docs/evidence/d000-track2/*, docs/prior-art/micropsi2/*, SELECTION_LEDGER, .agent/*, .gitignore
- Next action: commit Track 2, seal, then open Track 3 Hexis

## Repo facts needed now
- Mimir project ID: 7777645d52a91b49
- Seal task ID: edd30db7ba6d4e1d84d966ea3a13de09
- Track 2 tests: 23 passed
- Upstream clones gitignored (not committed)

## Last validation
- Command: `python3 -m pytest docs/prior-art/homeostatic-rl/formal_reproduction/test_track2.py -q`
- Result: 23 passed

## Open blockers
- D-001 remains blocked
- Track 3 blocked until seal completes
- Operator RECORD entries requested after Track 2 commit
