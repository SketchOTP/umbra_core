# Seed contract

- Seed: `7`.
- Purpose: bounded research-only equivalence run.
- Generator: `umbra_core.util.SeededRNG`, repository-pinned implementation.
- Entry: `OrganismConfig(seed=seed)` in the existing D-009 construction path.
- Secondary randomness: none declared for this subject.
- Authority: diagnostic only, never a qualification seed manifest.
- Rerun rule: the same definition and seed fingerprint must match exactly;
  changing the seed is rejected before comparison.
- Canonical D-009 `seed-manifest.json` is reference truth and is not regenerated.
